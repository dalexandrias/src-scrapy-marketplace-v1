"""
Gerenciador do banco de dados SQLite
Responsável por todas as operações com o banco de dados
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'marketplace.db')
        
        self.db_path = db_path
        self.schema_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'database.sql')
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Inicializar banco se necessário
        self._initialize_database()
    
    def _initialize_database(self):
        """Inicializar banco de dados com schema"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
                
            print(f"✅ Banco de dados inicializado: {self.db_path}")
        except Exception as e:
            print(f"❌ Erro ao inicializar banco: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões com o banco"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acesso por nome da coluna
        try:
            yield conn
        finally:
            conn.close()
    
    # =================================================================
    # CONFIGURAÇÕES
    # =================================================================
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Obter valor de configuração"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                value = row['value']
                # Tentar converter para tipos apropriados
                if value.lower() in ('true', 'false'):
                    return value.lower() == 'true'
                try:
                    return int(value)
                except ValueError:
                    try:
                        return float(value)
                    except ValueError:
                        return value
            
            return default
    
    def set_config(self, key: str, value: Any, description: str = None):
        """Definir valor de configuração"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO config (key, value, description) 
                VALUES (?, ?, ?)
            """, (key, str(value), description))
            conn.commit()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obter todas as configurações"""
        configs = {}
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM config")
            for row in cursor.fetchall():
                configs[row['key']] = self.get_config(row['key'])
        return configs
    
    # =================================================================
    # CIDADES
    # =================================================================
    
    def add_city(self, name: str, facebook_slug: str, active: bool = True) -> int:
        """Adicionar nova cidade"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO cities (name, facebook_slug, active) 
                VALUES (?, ?, ?)
            """, (name, facebook_slug, active))
            conn.commit()
            return cursor.lastrowid
    
    def get_cities(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Obter lista de cidades"""
        query = "SELECT * FROM cities"
        params = []
        
        if active_only:
            query += " WHERE active = 1"
        
        query += " ORDER BY name"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_city_by_slug(self, facebook_slug: str) -> Optional[Dict[str, Any]]:
        """Obter cidade por slug do Facebook"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM cities WHERE facebook_slug = ?
            """, (facebook_slug,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_city_status(self, city_id: int, active: bool):
        """Atualizar status de uma cidade"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE cities SET active = ? WHERE id = ?
            """, (active, city_id))
            conn.commit()
    
    # =================================================================
    # PALAVRAS-CHAVE
    # =================================================================
    
    def add_keyword(self, term: str, check_interval: int = 120, active: bool = True) -> int:
        """Adicionar nova palavra-chave"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO keywords (term, check_interval, active) 
                VALUES (?, ?, ?)
            """, (term, check_interval, active))
            conn.commit()
            return cursor.lastrowid
    
    def get_keywords(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Obter lista de palavras-chave"""
        query = "SELECT * FROM keywords"
        params = []
        
        if active_only:
            query += " WHERE active = 1"
        
        query += " ORDER BY term"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_keywords_to_check(self) -> List[Dict[str, Any]]:
        """Obter palavras-chave que precisam ser verificadas"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM keywords 
                WHERE active = 1 
                AND (
                    last_check IS NULL 
                    OR datetime(last_check, '+' || check_interval || ' seconds') <= datetime('now')
                )
                ORDER BY last_check ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_keyword_check(self, keyword_id: int):
        """Atualizar timestamp da última verificação"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE keywords 
                SET last_check = CURRENT_TIMESTAMP,
                    total_checks = total_checks + 1
                WHERE id = ?
            """, (keyword_id,))
            conn.commit()
    
    def update_keyword_interval(self, keyword_id: int, check_interval: int):
        """Atualizar intervalo de verificação"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE keywords SET check_interval = ? WHERE id = ?
            """, (check_interval, keyword_id))
            conn.commit()
    
    # =================================================================
    # ANÚNCIOS
    # =================================================================
    
    def add_listing(self, facebook_id: str, title: str, price: str, url: str, 
                   city_id: int, keyword_id: int, description: str = None, 
                   location: str = None, image_url: str = None) -> int:
        """Adicionar novo anúncio"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO listings 
                (facebook_id, title, price, url, description, location, image_url, city_id, keyword_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (facebook_id, title, price, url, description, location, image_url, city_id, keyword_id))
            conn.commit()
            
            # Atualizar contador de encontrados
            conn.execute("""
                UPDATE keywords SET total_found = total_found + 1 WHERE id = ?
            """, (keyword_id,))
            conn.commit()
            
            return cursor.lastrowid
    
    def listing_exists(self, facebook_id: str) -> bool:
        """Verificar se anúncio já existe"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 1 FROM listings WHERE facebook_id = ?
            """, (facebook_id,))
            return cursor.fetchone() is not None
    
    def get_recent_listings(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Obter anúncios recentes"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT l.*, c.name as city_name, k.term as keyword_term
                FROM listings l
                LEFT JOIN cities c ON l.city_id = c.id
                LEFT JOIN keywords k ON l.keyword_id = k.id
                WHERE l.found_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY l.found_at DESC
                LIMIT ?
            """, (hours, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_listing_notified(self, listing_id: int):
        """Marcar anúncio como notificado"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE listings 
                SET notified = 1, notified_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (listing_id,))
            conn.commit()
    
    def get_unnotified_listings(self) -> List[Dict[str, Any]]:
        """Obter anúncios não notificados"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT l.*, c.name as city_name, k.term as keyword_term
                FROM listings l
                LEFT JOIN cities c ON l.city_id = c.id
                LEFT JOIN keywords k ON l.keyword_id = k.id
                WHERE l.notified = 0
                ORDER BY l.found_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # =================================================================
    # LOGS
    # =================================================================
    
    def add_log(self, level: str, message: str, module: str = None, 
                function: str = None, details: Dict = None):
        """Adicionar entrada de log"""
        details_json = json.dumps(details) if details else None
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO system_logs (level, message, module, function, details) 
                VALUES (?, ?, ?, ?, ?)
            """, (level, message, module, function, details_json))
            conn.commit()
    
    def get_logs(self, level: str = None, hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """Obter logs do sistema"""
        query = """
            SELECT * FROM system_logs 
            WHERE created_at >= datetime('now', '-' || ? || ' hours')
        """
        params = [hours]
        
        if level:
            query += " AND level = ?"
            params.append(level)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_logs(self, days: int = 30):
        """Limpar logs antigos"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM system_logs 
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            return cursor.rowcount
    
    # =================================================================
    # ESTATÍSTICAS
    # =================================================================
    
    def add_execution_stat(self, keyword_id: int, city_id: int, execution_time_ms: int, 
                          listings_found: int, new_listings: int, errors: int = 0):
        """Adicionar estatística de execução"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO execution_stats 
                (keyword_id, city_id, execution_time_ms, listings_found, new_listings, errors) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (keyword_id, city_id, execution_time_ms, listings_found, new_listings, errors))
            conn.commit()
    
    def get_stats_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Obter resumo de estatísticas"""
        with self.get_connection() as conn:
            # Estatísticas gerais
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_executions,
                    AVG(execution_time_ms) as avg_execution_time,
                    SUM(listings_found) as total_listings_found,
                    SUM(new_listings) as total_new_listings,
                    SUM(errors) as total_errors
                FROM execution_stats 
                WHERE executed_at >= datetime('now', '-' || ? || ' hours')
            """, (hours,))
            
            stats = dict(cursor.fetchone())
            
            # Top keywords
            cursor = conn.execute("""
                SELECT k.term, SUM(es.new_listings) as new_listings
                FROM execution_stats es
                JOIN keywords k ON es.keyword_id = k.id
                WHERE es.executed_at >= datetime('now', '-' || ? || ' hours')
                GROUP BY k.term
                ORDER BY new_listings DESC
                LIMIT 5
            """, (hours,))
            
            stats['top_keywords'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    # =================================================================
    # NOTIFICAÇÕES
    # =================================================================
    
    def add_notification(self, listing_id: int, notification_type: str, 
                        message: str, status: str = 'pending') -> int:
        """Adicionar notificação"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO notifications (listing_id, type, message, status) 
                VALUES (?, ?, ?, ?)
            """, (listing_id, notification_type, message, status))
            conn.commit()
            return cursor.lastrowid
    
    def update_notification_status(self, notification_id: int, status: str, 
                                  error_message: str = None):
        """Atualizar status de notificação"""
        with self.get_connection() as conn:
            if status == 'sent':
                conn.execute("""
                    UPDATE notifications 
                    SET status = ?, sent_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                """, (status, error_message, notification_id))
            else:
                conn.execute("""
                    UPDATE notifications 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                """, (status, error_message, notification_id))
            conn.commit()
    
    # =================================================================
    # UTILITÁRIOS
    # =================================================================
    
    def get_database_info(self) -> Dict[str, Any]:
        """Obter informações sobre o banco"""
        with self.get_connection() as conn:
            info = {}
            
            # Tamanho do arquivo
            info['file_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            # Contadores de tabelas
            tables = ['cities', 'keywords', 'listings', 'system_logs', 'notifications', 'execution_stats']
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                info[f'{table}_count'] = cursor.fetchone()['count']
            
            # Versão do schema
            info['schema_version'] = self.get_config('database_version', '1.0')
            
            return info
    
    def backup_database(self, backup_path: str):
        """Fazer backup do banco de dados"""
        import shutil
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def get_city_by_slug(self, slug: str) -> Dict[str, Any]:
        """Buscar cidade por slug"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM cities WHERE facebook_slug = ?
            """, (slug,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_city_status(self, city_id: int, active: bool):
        """Atualizar status da cidade"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE cities SET active = ? WHERE id = ?
            """, (active, city_id))
            conn.commit()
    
    def update_keyword_interval(self, keyword_id: int, interval: int):
        """Atualizar intervalo da palavra-chave"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE keywords SET check_interval = ? WHERE id = ?
            """, (interval, keyword_id))
            conn.commit()
    
    def get_recent_listings(self, hours: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Obter anúncios recentes"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT l.*, k.term as keyword_term 
                FROM listings l
                LEFT JOIN keywords k ON l.keyword_id = k.id
                WHERE l.found_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY l.found_at DESC
                LIMIT ?
            """, (hours, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obter todas as configurações"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM config")
            return {row['key']: row['value'] for row in cursor.fetchall()}
