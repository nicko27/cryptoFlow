"""
API Client pour Telegram [FIXED avec retry]
"""

import requests
import time
from typing import Optional, BinaryIO
from core.models import Alert
import logging

logger = logging.getLogger("CryptoBot.TelegramAPI")


class TelegramAPI:
    """Client API Telegram avec retry logic"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 10):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
        
        # Statistiques
        self._messages_sent = 0
        self._errors = 0
    
    def _retry_request(self, method: str, **kwargs) -> Optional[dict]:
        """Effectue une requête avec retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(method, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    return data
                else:
                    logger.warning(f"Telegram API returned ok=False: {data}")
                    return None
            
            except requests.exceptions.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Telegram request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY)
                    continue
                
                logger.error(f"Telegram request failed after {self.MAX_RETRIES} attempts: {e}")
                self._errors += 1
                return None
        
        return None
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Envoie un message texte"""
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            result = self._retry_request("POST", url=url, json=data)
            
            if result:
                self._messages_sent += 1
                logger.debug(f"Message sent successfully (total: {self._messages_sent})")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            self._errors += 1
            return False
    
    def send_photo(self, photo: BinaryIO, caption: str = "", parse_mode: str = "HTML") -> bool:
        """Envoie une photo avec caption"""
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram credentials not configured")
            return False
        
        try:
            url = f"{self.base_url}/sendPhoto"
            files = {'photo': ('chart.png', photo, 'image/png')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': parse_mode
            }
            
            result = self._retry_request("POST", url=url, files=files, data=data)
            
            if result:
                self._messages_sent += 1
                logger.debug("Photo sent successfully")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error sending photo: {e}", exc_info=True)
            self._errors += 1
            return False
    
    def send_alert(self, alert: Alert, include_metadata: bool = False) -> bool:
        """Envoie une alerte formatée"""
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "important": "🔔",
            "critical": "🚨"
        }
        
        emoji = emoji_map.get(alert.alert_level.value, "📢")
        
        message = f"{emoji} <b>{alert.alert_type.value.upper()}</b>\n\n"
        message += f"<b>{alert.symbol}</b>\n"
        message += f"{alert.message}\n\n"
        message += f"<i>{alert.timestamp.strftime('%H:%M:%S')}</i>"
        
        if include_metadata and alert.metadata:
            message += "\n\n<b>Détails:</b>\n"
            for key, value in alert.metadata.items():
                if isinstance(value, float):
                    message += f"  • {key}: {value:.4f}\n"
                else:
                    message += f"  • {key}: {value}\n"
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """Teste la connexion au bot"""
        try:
            url = f"{self.base_url}/getMe"
            result = self._retry_request("GET", url=url)
            
            if result:
                logger.info(f"Telegram bot connected: {result.get('result', {}).get('username')}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error testing connection: {e}", exc_info=True)
            return False
    
    def get_bot_info(self) -> Optional[dict]:
        """Récupère les infos du bot"""
        try:
            url = f"{self.base_url}/getMe"
            result = self._retry_request("GET", url=url)
            
            if result:
                return result.get("result", {})
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting bot info: {e}", exc_info=True)
            return None
    
    def get_stats(self) -> dict:
        """Retourne les statistiques"""
        return {
            "messages_sent": self._messages_sent,
            "errors": self._errors
        }
