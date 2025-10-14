"""
API Client pour Telegram
"""

import requests
from typing import Optional, BinaryIO
from core.models import Alert


class TelegramAPI:
    """Client API Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 10):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Envoie un message texte"""
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get("ok", False)
        
        except Exception as e:
            print(f"Erreur envoi message Telegram: {e}")
            return False
    
    def send_photo(self, photo: BinaryIO, caption: str = "", parse_mode: str = "HTML") -> bool:
        """Envoie une photo avec caption"""
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendPhoto"
            files = {'photo': ('chart.png', photo, 'image/png')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': parse_mode
            }
            
            response = self.session.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
            
            return response.json().get("ok", False)
        
        except Exception as e:
            print(f"Erreur envoi photo Telegram: {e}")
            return False
    
    def send_alert(self, alert: Alert, include_metadata: bool = False) -> bool:
        """Envoie une alerte formatée"""
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "IMPORTANT": "🔔",
            "CRITICAL": "🚨"
        }
        
        emoji = emoji_map.get(alert.alert_level.value.upper(), "📢")
        
        message = f"{emoji} <b>{alert.alert_type.value.upper()}</b>\n\n"
        message += f"<b>{alert.symbol}</b>\n"
        message += f"{alert.message}\n\n"
        message += f"<i>{alert.timestamp.strftime('%H:%M:%S')}</i>"
        
        if include_metadata and alert.metadata:
            message += "\n\n<b>Détails:</b>\n"
            for key, value in alert.metadata.items():
                message += f"  • {key}: {value}\n"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Teste la connexion au bot"""
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get("ok", False)
        
        except Exception as e:
            print(f"Erreur test connexion Telegram: {e}")
            return False
    
    def get_bot_info(self) -> Optional[dict]:
        """Récupère les infos du bot"""
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get("ok"):
                return data.get("result", {})
            
            return None
        
        except Exception as e:
            print(f"Erreur récupération infos bot: {e}")
            return None
