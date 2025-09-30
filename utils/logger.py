"""
Sistema de logging personalizado para o monitoramento
Integra com o banco de dados e fornece logs coloridos
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ColoredFormatter(logging.Formatter):
    """Formatter que adiciona cores aos logs no terminal"""
    
    # Códigos de cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Ciano
        'INFO': '\033[32m',       # Verde
        'WARNING': '\033[33m',    # Amarelo
        'ERROR': '\033[31m',      # Vermelho
        'CRITICAL': '\033[41m',   # Fundo vermelho
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Adicionar cor ao nível
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Criar formato colorido
        colored_levelname = f"{log_color}{record.levelname:<8}{reset_color}"
        
        # Substituir o levelname original
        original_levelname = record.levelname
        record.levelname = colored_levelname
        
        # Formatear mensagem
        formatted = super().format(record)
        
        # Restaurar levelname original
        record.levelname = original_levelname
        
        return formatted

class Logger:
    def __init__(self, name: str = "MarketplaceMonitor", db_manager=None):
        self.name = name
        self.db_manager = db_manager
        
        # Configurar logger do Python
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configurar handlers de console e arquivo"""
        
        # Handler para console (colorido)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Handler para arquivo
        file_handler = logging.FileHandler('marketplace_monitor.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Adicionar handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def _log_to_db(self, level: str, message: str, module: str = None, 
                   function: str = None, details: Dict[str, Any] = None):
        """Salvar log no banco de dados"""
        if self.db_manager:
            try:
                self.db_manager.add_log(level, message, module, function, details)
            except Exception as e:
                # Evitar loop infinito se houver erro no banco
                print(f"Erro ao salvar log no banco: {e}")
    
    def debug(self, message: str, module: str = None, function: str = None, 
              details: Dict[str, Any] = None):
        """Log de debug"""
        self.logger.debug(message)
        self._log_to_db(LogLevel.DEBUG.value, message, module, function, details)
    
    def info(self, message: str, module: str = None, function: str = None, 
             details: Dict[str, Any] = None):
        """Log de informação"""
        self.logger.info(message)
        self._log_to_db(LogLevel.INFO.value, message, module, function, details)
    
    def warning(self, message: str, module: str = None, function: str = None, 
                details: Dict[str, Any] = None):
        """Log de aviso"""
        self.logger.warning(message)
        self._log_to_db(LogLevel.WARNING.value, message, module, function, details)
    
    def error(self, message: str, module: str = None, function: str = None, 
              details: Dict[str, Any] = None):
        """Log de erro"""
        self.logger.error(message)
        self._log_to_db(LogLevel.ERROR.value, message, module, function, details)
    
    def critical(self, message: str, module: str = None, function: str = None, 
                 details: Dict[str, Any] = None):
        """Log crítico"""
        self.logger.critical(message)
        self._log_to_db(LogLevel.CRITICAL.value, message, module, function, details)
    
    def log_execution_start(self, operation: str, **kwargs):
        """Log início de operação"""
        details = {
            'operation': operation,
            'parameters': kwargs,
            'start_time': datetime.now().isoformat()
        }
        self.info(f"🚀 Iniciando: {operation}", details=details)
        return details
    
    def log_execution_end(self, operation: str, success: bool, 
                         execution_details: Dict[str, Any] = None, **kwargs):
        """Log fim de operação"""
        status = "✅ Sucesso" if success else "❌ Falha"
        
        details = {
            'operation': operation,
            'success': success,
            'end_time': datetime.now().isoformat()
        }
        
        if execution_details:
            details.update(execution_details)
        
        if kwargs:
            details.update(kwargs)
        
        level_func = self.info if success else self.error
        level_func(f"{status}: {operation}", details=details)
    
    def log_scraping_result(self, keyword: str, city: str, result: Dict[str, Any]):
        """Log específico para resultados de scraping"""
        message = (f"🔍 {keyword} em {city}: "
                  f"{result.get('new_listings', 0)} novos/"
                  f"{result.get('listings_found', 0)} total "
                  f"({result.get('execution_time_ms', 0)}ms)")
        
        if result.get('success'):
            self.info(message, details=result)
        else:
            self.error(f"❌ {message} - {result.get('error_message', 'Erro desconhecido')}", 
                      details=result)
    
    def log_notification_sent(self, notification_type: str, listing_title: str, 
                             success: bool, error: str = None):
        """Log para notificações enviadas"""
        status = "✅" if success else "❌"
        message = f"{status} Notificação {notification_type}: {listing_title[:50]}"
        
        details = {
            'notification_type': notification_type,
            'listing_title': listing_title,
            'success': success,
            'error': error
        }
        
        if success:
            self.info(message, details=details)
        else:
            self.error(f"{message} - {error}", details=details)
    
    def set_level(self, level: str):
        """Definir nível de log"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self.logger.setLevel(level_map[level.upper()])
            # Atualizar handlers também
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(level_map[level.upper()])

# Instância global do logger
_global_logger = None

def get_logger(name: str = "MarketplaceMonitor", db_manager=None) -> Logger:
    """Obter instância do logger"""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = Logger(name, db_manager)
    elif db_manager and not _global_logger.db_manager:
        _global_logger.db_manager = db_manager
    
    return _global_logger
