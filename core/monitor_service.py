"""
Serviço principal de monitoramento
Controla o loop de verificação e coordena todos os componentes
"""

import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
from threading import Event

from .db_manager import DatabaseManager
from .scraper_engine import ScraperEngine
from utils.logger import get_logger
from notifications.base import NotificationManager
from notifications.console import ConsoleNotifier
from notifications.file import FileNotifier

class MonitorService:
    """Serviço principal de monitoramento"""
    
    def __init__(self, db_path: str = None):
        # Inicializar componentes
        self.db = DatabaseManager(db_path)
        self.logger = get_logger("MonitorService", self.db)
        self.scraper = ScraperEngine(self.db, self.logger)
        
        # Estado do serviço
        self.running = False
        self.stop_event = Event()
        
        # Configurações
        self._load_config()
        
        # Configurar notificações
        self._setup_notifications()
        
        # Configurar handlers de sinais
        self._setup_signal_handlers()
    
    def _load_config(self):
        """Carregar configurações do banco"""
        self.config = {
            'check_interval_default': self.db.get_config('check_interval_default', 120),
            'max_retries': self.db.get_config('max_retries', 3),
            'notification_enabled': self.db.get_config('notification_enabled', True),
            'log_level': self.db.get_config('log_level', 'INFO'),
            'cleanup_logs_days': self.db.get_config('cleanup_logs_days', 30)
        }
        
        # Aplicar nível de log
        self.logger.set_level(self.config['log_level'])
        
        self.logger.info("Configurações carregadas do banco de dados")
    
    def _setup_notifications(self):
        """Configurar sistema de notificações"""
        self.notification_manager = NotificationManager(self.db, self.logger)
        
        if self.config['notification_enabled']:
            # Obter tipos de notificação habilitados
            notification_types = self.db.get_config('notification_types', 'console,file')
            types_list = [t.strip() for t in notification_types.split(',')]
            
            # Configurar notificadores
            if 'console' in types_list:
                console_config = {
                    'show_details': self.db.get_config('console_show_details', False),
                    'use_colors': self.db.get_config('console_use_colors', True)
                }
                self.notification_manager.add_notifier(ConsoleNotifier(console_config))
            
            if 'file' in types_list:
                file_config = {
                    'file_path': self.db.get_config('file_notification_path', 'data/notifications.json'),
                    'format': self.db.get_config('file_notification_format', 'json'),
                    'append_mode': self.db.get_config('file_notification_append', True)
                }
                self.notification_manager.add_notifier(FileNotifier(file_config))
        
        self.logger.info(f"Sistema de notificações configurado com {len(self.notification_manager.notifiers)} notificadores")
    
    def _setup_signal_handlers(self):
        """Configurar handlers para sinais do sistema"""
        def signal_handler(signum, frame):
            self.logger.info(f"Sinal {signum} recebido. Parando serviço...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)  # Termination
    
    def get_status(self) -> Dict[str, Any]:
        """Obter status do serviço"""
        # Estatísticas recentes
        stats = self.db.get_stats_summary(24)
        
        # Próximas verificações
        keywords_to_check = self.db.get_keywords_to_check()
        next_checks = []
        
        for keyword in keywords_to_check[:5]:  # Próximas 5
            if keyword['last_check']:
                last_check = datetime.fromisoformat(keyword['last_check'])
                next_check = last_check + timedelta(seconds=keyword['check_interval'])
            else:
                next_check = datetime.now()
            
            next_checks.append({
                'keyword': keyword['term'],
                'next_check': next_check.strftime('%H:%M:%S'),
                'interval': keyword['check_interval']
            })
        
        return {
            'running': self.running,
            'uptime': self._get_uptime(),
            'stats_24h': stats,
            'next_checks': next_checks,
            'database_info': self.db.get_database_info(),
            'config': self.config
        }
    
    def _get_uptime(self) -> str:
        """Obter tempo de execução"""
        if hasattr(self, 'start_time'):
            uptime_seconds = int(time.time() - self.start_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    def check_keyword_city_combination(self, keyword: Dict[str, Any], city: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar uma combinação específica de palavra-chave e cidade"""
        self.logger.debug(f"Verificando '{keyword['term']}' em {city['name']}")
        
        try:
            result = self.scraper.scrape_marketplace(
                city_slug=city['facebook_slug'],
                keyword=keyword['term'],
                city_id=city['id'],
                keyword_id=keyword['id']
            )
            
            # Log do resultado
            self.logger.log_scraping_result(keyword['term'], city['name'], result)
            
            return result
            
        except Exception as e:
            error_msg = f"Erro ao verificar {keyword['term']} em {city['name']}: {e}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error_message': error_msg,
                'listings_found': 0,
                'new_listings': 0,
                'errors': 1,
                'execution_time_ms': 0
            }
    
    def process_keyword(self, keyword: Dict[str, Any]) -> Dict[str, Any]:
        """Processar uma palavra-chave em todas as cidades ativas"""
        cities = self.db.get_cities(active_only=True)
        
        total_new = 0
        total_found = 0
        total_errors = 0
        execution_time = 0
        
        self.logger.info(f"🔍 Processando '{keyword['term']}' em {len(cities)} cidades")
        
        for city in cities:
            result = self.check_keyword_city_combination(keyword, city)
            
            total_new += result.get('new_listings', 0)
            total_found += result.get('listings_found', 0)
            total_errors += result.get('errors', 0)
            execution_time += result.get('execution_time_ms', 0)
            
            # Delay entre cidades para evitar sobrecarga
            if not self.stop_event.is_set():
                time.sleep(2)
        
        # Atualizar timestamp da última verificação
        self.db.update_keyword_check(keyword['id'])
        
        summary = {
            'keyword': keyword['term'],
            'cities_checked': len(cities),
            'total_new': total_new,
            'total_found': total_found,
            'total_errors': total_errors,
            'execution_time_ms': execution_time
        }
        
        if total_new > 0:
            self.logger.info(f"✅ {keyword['term']}: {total_new} novos anúncios encontrados!")
        
        return summary
    
    def process_notifications(self):
        """Processar notificações pendentes"""
        unnotified = self.db.get_unnotified_listings()
        
        if unnotified:
            self.logger.info(f"📢 Enviando {len(unnotified)} notificações pendentes")
            
            for listing in unnotified:
                try:
                    # Enviar notificação
                    self.notification_manager.send_notification(listing)
                    
                    # Marcar como notificado
                    self.db.mark_listing_notified(listing['id'])
                    
                except Exception as e:
                    self.logger.error(f"Erro ao notificar anúncio {listing['id']}: {e}")
    
    def cleanup_old_data(self):
        """Limpeza de dados antigos"""
        try:
            days = self.config['cleanup_logs_days']
            removed_logs = self.db.cleanup_old_logs(days)
            
            if removed_logs > 0:
                self.logger.info(f"🧹 Limpeza: {removed_logs} logs antigos removidos")
                
        except Exception as e:
            self.logger.error(f"Erro na limpeza: {e}")
    
    def monitoring_cycle(self):
        """Executar um ciclo completo de monitoramento"""
        cycle_start = time.time()
        
        try:
            # Obter palavras-chave que precisam ser verificadas
            keywords_to_check = self.db.get_keywords_to_check()
            
            if not keywords_to_check:
                self.logger.debug("Nenhuma palavra-chave para verificar no momento")
                return
            
            self.logger.info(f"🚀 Iniciando ciclo: {len(keywords_to_check)} palavras-chave para verificar")
            
            total_new_listings = 0
            
            # Processar cada palavra-chave
            for keyword in keywords_to_check:
                if self.stop_event.is_set():
                    break
                
                summary = self.process_keyword(keyword)
                total_new_listings += summary['total_new']
                
                # Delay entre palavras-chave
                if not self.stop_event.is_set():
                    time.sleep(5)
            
            # Processar notificações
            if not self.stop_event.is_set():
                self.process_notifications()
            
            # Limpeza periódica (a cada 10 ciclos)
            if not self.stop_event.is_set() and hasattr(self, 'cycle_count'):
                self.cycle_count += 1
                if self.cycle_count % 10 == 0:
                    self.cleanup_old_data()
            
            cycle_time = int((time.time() - cycle_start) * 1000)
            
            if total_new_listings > 0:
                self.logger.info(f"🎉 Ciclo concluído: {total_new_listings} novos anúncios em {cycle_time}ms")
            else:
                self.logger.info(f"✅ Ciclo concluído: nenhum anúncio novo em {cycle_time}ms")
                
        except Exception as e:
            self.logger.error(f"Erro no ciclo de monitoramento: {e}")
    
    def start(self):
        """Iniciar o serviço de monitoramento"""
        if self.running:
            self.logger.warning("Serviço já está executando")
            return
        
        self.logger.info("🚀 Iniciando serviço de monitoramento do Facebook Marketplace")
        
        # Marcar estado
        self.running = True
        self.start_time = time.time()
        self.cycle_count = 0
        self.stop_event.clear()
        
        # Log de configurações iniciais
        self.logger.info(f"Configurações: intervalo padrão {self.config['check_interval_default']}s")
        
        try:
            while not self.stop_event.is_set():
                # Executar ciclo de monitoramento
                self.monitoring_cycle()
                
                # Aguardar próximo ciclo (mínimo 30 segundos)
                sleep_time = max(30, self.config['check_interval_default'] // 4)
                
                for _ in range(sleep_time):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("Interrupção por teclado recebida")
        except Exception as e:
            self.logger.error(f"Erro crítico no serviço: {e}")
        finally:
            self._cleanup()
    
    def stop(self):
        """Parar o serviço"""
        if not self.running:
            self.logger.warning("Serviço não está executando")
            return
        
        self.logger.info("🛑 Parando serviço de monitoramento...")
        self.stop_event.set()
        self.running = False
    
    def _cleanup(self):
        """Limpeza final"""
        self.logger.info("🧹 Executando limpeza final...")
        
        # Fechar driver do scraper
        if self.scraper:
            self.scraper.close_driver()
        
        # Estatísticas finais
        if hasattr(self, 'start_time'):
            uptime = self._get_uptime()
            self.logger.info(f"⏱️  Tempo total de execução: {uptime}")
        
        self.logger.info("✅ Serviço finalizado")
        self.running = False
