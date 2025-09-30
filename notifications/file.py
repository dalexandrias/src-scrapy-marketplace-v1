"""
Notificador para arquivo
Salva notificações em arquivos JSON ou texto
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
from .base import BaseNotifier, NotificationData

class FileNotifier(BaseNotifier):
    """Notificador que salva em arquivo"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.file_path = self.config.get('file_path', 'notifications.json')
        self.format = self.config.get('format', 'json')  # json ou txt
        self.append_mode = self.config.get('append_mode', True)
        
        # Criar diretório se necessário
        os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
    
    def get_type(self) -> str:
        return "file"
    
    def send(self, notification_data: NotificationData) -> Dict[str, Any]:
        """Salvar notificação em arquivo"""
        try:
            if self.format.lower() == 'json':
                return self._save_json(notification_data)
            else:
                return self._save_text(notification_data)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Erro ao salvar em arquivo: {e}"
            }
    
    def _save_json(self, notification_data: NotificationData) -> Dict[str, Any]:
        """Salvar em formato JSON"""
        data = notification_data.to_dict()
        
        if self.append_mode and os.path.exists(self.file_path):
            # Ler arquivo existente
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
            
            # Adicionar nova notificação
            existing_data.append(data)
            
            # Salvar arquivo atualizado
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        else:
            # Salvar apenas a nova notificação
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {
            'success': True,
            'message': f'Notificação salva em {self.file_path}'
        }
    
    def _save_text(self, notification_data: NotificationData) -> Dict[str, Any]:
        """Salvar em formato texto"""
        listing = notification_data.listing
        
        # Formatar texto
        lines = [
            f"=====================================",
            f"NOVA NOTIFICAÇÃO - {notification_data.timestamp.strftime('%d/%m/%Y %H:%M:%S')}",
            f"=====================================",
            f"Palavra-chave: {listing.get('keyword_term', 'N/A')}",
            f"Cidade: {listing.get('city_name', 'N/A')}",
            f"",
            f"Título: {listing.get('title', 'Sem título')}",
            f"Preço: {listing.get('price', 'Não informado')}",
            f"Localização: {listing.get('location', 'Não informada')}",
            f"",
            f"Link: {listing.get('url', 'N/A')}",
            f"ID Facebook: {listing.get('facebook_id', 'N/A')}",
            f"",
            f""
        ]
        
        text_content = "\n".join(lines)
        
        # Salvar arquivo
        mode = 'a' if self.append_mode else 'w'
        with open(self.file_path, mode, encoding='utf-8') as f:
            f.write(text_content)
        
        return {
            'success': True,
            'message': f'Notificação salva em {self.file_path}'
        }
