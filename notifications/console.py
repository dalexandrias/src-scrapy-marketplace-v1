"""
Notificador para console
Exibe notificações coloridas no terminal
"""

import json
from datetime import datetime
from typing import Dict, Any
from .base import BaseNotifier, NotificationData

class ConsoleNotifier(BaseNotifier):
    """Notificador que exibe mensagens no console"""
    
    # Códigos de cores ANSI
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RESET': '\033[0m'
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.show_details = self.config.get('show_details', True)
        self.use_colors = self.config.get('use_colors', True)
    
    def get_type(self) -> str:
        return "console"
    
    def colorize(self, text: str, color: str) -> str:
        """Adicionar cor ao texto se habilitado"""
        if not self.use_colors:
            return text
        
        color_code = self.COLORS.get(color.upper(), '')
        reset_code = self.COLORS['RESET']
        return f"{color_code}{text}{reset_code}"
    
    def format_detailed_message(self, notification_data: NotificationData) -> str:
        """Formatar mensagem detalhada"""
        listing = notification_data.listing
        
        # Cabeçalho
        header = self.colorize("🔔 NOVO ANÚNCIO ENCONTRADO", "BOLD")
        separator = self.colorize("=" * 60, "CYAN")
        
        # Informações principais
        keyword = self.colorize(f"Palavra-chave: {listing.get('keyword_term', 'N/A')}", "YELLOW")
        city = self.colorize(f"Cidade: {listing.get('city_name', 'N/A')}", "BLUE")
        timestamp = self.colorize(f"Encontrado em: {notification_data.timestamp.strftime('%d/%m/%Y %H:%M:%S')}", "CYAN")
        
        # Detalhes do anúncio
        title = self.colorize(f"Título: {listing.get('title', 'Sem título')}", "GREEN")
        price = listing.get('price')
        price_line = self.colorize(f"Preço: {price if price else 'Não informado'}", "GREEN")
        
        location = listing.get('location')
        location_line = f"Localização: {location if location else 'Não informada'}"
        
        url = listing.get('url', '')
        url_line = self.colorize(f"Link: {url}", "UNDERLINE")
        
        # Montar mensagem
        lines = [
            "",
            separator,
            header,
            separator,
            keyword,
            city,
            timestamp,
            "",
            title,
            price_line,
            location_line,
            "",
            url_line,
            separator,
            ""
        ]
        
        return "\n".join(lines)
    
    def format_simple_message(self, notification_data: NotificationData) -> str:
        """Formatar mensagem simples"""
        listing = notification_data.listing
        
        # Emoji baseado no preço
        price_emoji = "💰" if listing.get('price') else "📦"
        
        # Informações básicas
        keyword = listing.get('keyword_term', 'N/A')
        city = listing.get('city_name', 'N/A')
        title = listing.get('title', 'Sem título')[:50]
        price = listing.get('price', 'Preço não informado')
        
        if len(title) > 47:
            title += "..."
        
        # Formatar com cores
        time_str = notification_data.timestamp.strftime('%H:%M:%S')
        time_colored = self.colorize(f"[{time_str}]", "CYAN")
        keyword_colored = self.colorize(keyword, "YELLOW")
        city_colored = self.colorize(city, "BLUE")
        title_colored = self.colorize(title, "GREEN")
        price_colored = self.colorize(price, "GREEN")
        
        return f"{time_colored} {price_emoji} {keyword_colored} em {city_colored}: {title_colored} - {price_colored}"
    
    def send(self, notification_data: NotificationData) -> Dict[str, Any]:
        """Enviar notificação para o console"""
        try:
            if self.show_details:
                message = self.format_detailed_message(notification_data)
            else:
                message = self.format_simple_message(notification_data)
            
            print(message)
            
            return {
                'success': True,
                'message': 'Notificação exibida no console'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Erro ao exibir no console: {e}"
            }
