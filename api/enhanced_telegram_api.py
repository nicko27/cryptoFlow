"""
Enhanced Telegram API - Avec retry logic et message queue
"""

import requests
import time
from typing import Optional, BinaryIO, List
from queue import Queue, Empty
from threading import Thread, Lock
from core.models import Alert


class EnhancedTelegramAPI:
    """Client API Telegram amélioré avec retry et queue"""
    
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 10,
                 max_retries: int = 3, retry_delay: int = 2,
                 message_delay: float = 0.5):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.message_delay = message_delay
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = requests.Session()
        
        # Message queue
        self.message_queue = Queue()
        self.is_queue_active = False
        self.queue_thread: Optional[Thread] = None
        self.queue_lock = Lock()
        
        # Statistics
        self.stats = {
            "sent": 0,
            "failed": 0,
            "retries": 0,
            "queued": 0
        }
    
    def start_queue(self):
        """Démarre le worker de queue"""
        with self.queue_lock:
            if not self.is_queue_active:
                self.is_queue_active = True
                self.queue_thread = Thread(target=self._process_queue, daemon=True)
                self.queue_thread.start()
    
    def stop_queue(self):
        """Arrête le worker de queue"""
        with self.queue_lock:
            self.is_queue_active = False
            if self.queue_thread:
                self.queue_thread.join(timeout=5)
    
    def _process_queue(self):
        """Traite la queue de messages"""
        while self.is_queue_active:
            try:
                # Récupérer message (timeout 1s)
                message = self.message_queue.get(timeout=1)
                
                # Envoyer avec retry
                success = self._send_with_retry(
                    message["type"],
                    message["data"],
                    message.get("retries", 0)
                )
                
                if success:
                    self.stats["sent"] += 1
                else:
                    self.stats["failed"] += 1
                
                # Rate limiting configurable
                time.sleep(max(0.0, self.message_delay))
                
            except Empty:
                continue
            except Exception as e:
                print(f"Erreur traitement queue: {e}")
    
    def _send_with_retry(self, msg_type: str, data: dict, attempt: int = 0) -> bool:
        """Envoie un message avec retry logic"""
        
        for retry in range(self.max_retries):
            try:
                if msg_type == "text":
                    success = self._send_text(data["text"], data.get("parse_mode", "HTML"))
                elif msg_type == "photo":
                    success = self._send_photo_direct(data["photo"], data.get("caption", ""))
                elif msg_type == "alert":
                    success = self._send_alert_direct(data["alert"], data.get("include_metadata", False))
                else:
                    return False
                
                if success:
                    return True
                
                # Si échec, attendre avant retry
                if retry < self.max_retries - 1:
                    self.stats["retries"] += 1
                    time.sleep(self.retry_delay * (retry + 1))
            
            except Exception as e:
                print(f"Erreur envoi (tentative {retry + 1}): {e}")
                if retry < self.max_retries - 1:
                    time.sleep(self.retry_delay * (retry + 1))
        
        return False
    
    def send_message(self, text: str, parse_mode: str = "HTML", use_queue: bool = True) -> bool:
        """Envoie un message texte"""
        
        if use_queue and self.is_queue_active:
            self.message_queue.put({
                "type": "text",
                "data": {"text": text, "parse_mode": parse_mode}
            })
            self.stats["queued"] += 1
            return True
        
        return self._send_with_retry("text", {"text": text, "parse_mode": parse_mode})
    
    def _send_text(self, text: str, parse_mode: str) -> bool:
        """Envoie réellement le texte"""
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
            print(f"Erreur envoi message: {e}")
            return False
    
    def send_photo(self, photo: BinaryIO, caption: str = "", use_queue: bool = True) -> bool:
        """Envoie une photo"""
        
        if use_queue and self.is_queue_active:
            self.message_queue.put({
                "type": "photo",
                "data": {"photo": photo, "caption": caption}
            })
            self.stats["queued"] += 1
            return True
        
        return self._send_with_retry("photo", {"photo": photo, "caption": caption})
    
    def _send_photo_direct(self, photo: BinaryIO, caption: str) -> bool:
        """Envoie réellement la photo"""
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendPhoto"
            files = {'photo': ('chart.png', photo, 'image/png')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            response = self.session.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
            
            return response.json().get("ok", False)
        
        except Exception as e:
            print(f"Erreur envoi photo: {e}")
            return False
    
    def send_alert(self, alert: Alert, include_metadata: bool = False, 
                   use_queue: bool = True) -> bool:
        """Envoie une alerte"""
        
        if use_queue and self.is_queue_active:
            self.message_queue.put({
                "type": "alert",
                "data": {"alert": alert, "include_metadata": include_metadata}
            })
            self.stats["queued"] += 1
            return True
        
        return self._send_with_retry("alert", {
            "alert": alert, 
            "include_metadata": include_metadata
        })
    
    def _send_alert_direct(self, alert: Alert, include_metadata: bool) -> bool:
        """Envoie réellement l'alerte"""
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
        
        return self._send_text(message, "HTML")
    
    def test_connection(self) -> bool:
        """Teste la connexion"""
        try:
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get("ok", False)
        
        except Exception as e:
            print(f"Erreur test connexion: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Retourne les statistiques"""
        return {
            **self.stats,
            "queue_size": self.message_queue.qsize(),
            "queue_active": self.is_queue_active
        }
    
    def clear_queue(self):
        """Vide la queue"""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except Empty:
                break
