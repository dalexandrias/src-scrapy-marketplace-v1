"""
Sistema de notificações base
Define a interface comum para todos os tipos de notificação
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime

class NotificationData:
    """Classe para dados de notificação"""
    def __init__(self, listing: Dict[str, Any]):
        self.listing = listing
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            'type': 'new_listing',
            'timestamp': self.timestamp.isoformat(),
            'keyword': self.listing.get('keyword_term', ''),
            'city': self.listing.get('city_name', ''),
            'listing': {
                'id': self.listing.get('id'),
                'facebook_id': self.listing.get('facebook_id'),
                'title': self.listing.get('title', ''),
                'price': self.listing.get('price', ''),
                'url': self.listing.get('url', ''),
                'location': self.listing.get('location', ''),
                'found_at': self.listing.get('found_at', '')
            }
        }
        
    def get_summary(self) -> str:
        """Obter resumo da notificação"""
        title = self.listing.get('title', 'Sem título')
        price = self.listing.get('price', 'Preço não informado')
        keyword = self.listing.get('keyword_term', '')
        city = self.listing.get('city_name', '')
        
        return f"🔔 Novo anúncio para '{keyword}' em {city}: {title} - {price}"

class BaseNotifier(ABC):
    """Classe base para notificadores"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def send(self, notification_data: NotificationData) -> Dict[str, Any]:
        """
        Enviar notificação
        
        Returns:
            Dict com 'success' (bool), 'message' (str), 'error' (str opcional)
        """
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """Obter tipo do notificador"""
        pass
    
    def is_enabled(self) -> bool:
        """Verificar se notificador está habilitado"""
        return self.enabled
    
    def format_message(self, notification_data: NotificationData) -> str:
        """Formatar mensagem básica"""
        return notification_data.get_summary()

class NotificationManager:
    """Gerenciador central de notificações"""
    
    def __init__(self, db_manager, logger):
        self.db_manager = db_manager
        self.logger = logger
        self.notifiers: List[BaseNotifier] = []
        
    def add_notifier(self, notifier: BaseNotifier):
        """Adicionar notificador"""
        if notifier.is_enabled():
            self.notifiers.append(notifier)
            self.logger.info(f"Notificador {notifier.get_type()} adicionado")
        else:
            self.logger.info(f"Notificador {notifier.get_type()} desabilitado")
    
    def send_notification(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Enviar notificação para todos os notificadores"""
        notification_data = NotificationData(listing)
        results = {}
        
        for notifier in self.notifiers:
            try:
                result = notifier.send(notification_data)
                results[notifier.get_type()] = result
                
                # Salvar no banco de dados
                notification_id = self.db_manager.add_notification(
                    listing_id=listing['id'],
                    notification_type=notifier.get_type(),
                    message=notification_data.get_summary(),
                    status='pending'
                )
                
                # Atualizar status
                if result.get('success'):
                    self.db_manager.update_notification_status(
                        notification_id, 'sent'
                    )
                    self.logger.log_notification_sent(
                        notifier.get_type(), 
                        listing.get('title', ''), 
                        True
                    )
                else:
                    self.db_manager.update_notification_status(
                        notification_id, 'failed', result.get('error')
                    )
                    self.logger.log_notification_sent(
                        notifier.get_type(), 
                        listing.get('title', ''), 
                        False, 
                        result.get('error')
                    )
                    
            except Exception as e:
                error_msg = f"Erro no notificador {notifier.get_type()}: {e}"
                results[notifier.get_type()] = {
                    'success': False,
                    'error': error_msg
                }
                self.logger.error(error_msg)
        
        return results
    
    def send_batch_notifications(self, listings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enviar notificações em lote"""
        total_sent = 0
        total_failed = 0
        
        for listing in listings:
            results = self.send_notification(listing)
            
            # Contar sucessos e falhas
            for result in results.values():
                if result.get('success'):
                    total_sent += 1
                else:
                    total_failed += 1
        
        summary = {
            'total_listings': len(listings),
            'total_sent': total_sent,
            'total_failed': total_failed,
            'notifiers_count': len(self.notifiers)
        }
        
        self.logger.info(f"Lote de notificações: {total_sent} enviadas, {total_failed} falhas")
        return summary
