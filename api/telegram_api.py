"""API Telegram"""
import requests
from typing import Optional
from core.models import Alert

class TelegramAPI:
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 10):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("ok", False)
        except:
            return False
    
    def send_alert(self, alert: Alert, include_metadata: bool = False) -> bool:
        emoji_map = {"INFO": "ℹ️", "WARNING": "⚠️", "IMPORTANT": "🔔", "CRITICAL": "🚨"}
        emoji = emoji_map.get(alert.alert_level.value.upper(), "📢")
        message = f"{emoji} <b>{alert.alert_type.value.upper()}</b>\\n\\n<b>{alert.symbol}</b>\\n{alert.message}\\n\\n<i>{alert.timestamp.strftime('%H:%M:%S')}</i>"
        if include_metadata and alert.metadata:
            message += "\\n\\n<b>Détails:</b>\\n"
            for key, value in alert.metadata.items():
                message += f"  • {key}: {value}\\n"
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("ok", False)
        except:
            return False
