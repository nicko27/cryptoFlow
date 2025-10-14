"""Daemon Service - Exécution en arrière-plan"""
import time
import signal
import sys
from datetime import datetime, timezone
from typing import Optional
from threading import Event
from core.models import BotConfiguration, AlertLevel
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService

class DaemonService:
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.is_running = False
        self.stop_event = Event()
        self.binance_api = BinanceAPI()
        self.telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"Signal {signum} reçu, arrêt du démon...")
        self.stop()
    
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        print("🚀 CRYPTO BOT DAEMON DÉMARRÉ")
        print(f"Cryptos surveillées : {', '.join(self.config.crypto_symbols)}")
        try:
            self._run_loop()
        except Exception as e:
            print(f"Erreur fatale : {e}")
        finally:
            self._shutdown()
    
    def _run_loop(self):
        while self.is_running and not self.stop_event.is_set():
            try:
                for symbol in self.config.crypto_symbols:
                    market_data = self.market_service.get_market_data(symbol)
                    if market_data:
                        prediction = self.market_service.predict_price_movement(market_data)
                        alerts = self.alert_service.check_alerts(market_data, prediction)
                        for alert in alerts:
                            if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                                self.telegram_api.send_alert(alert, include_metadata=True)
                self.stop_event.wait(timeout=self.config.check_interval_seconds)
            except Exception as e:
                print(f"Erreur : {e}")
                time.sleep(60)
    
    def stop(self):
        print("🛑 Arrêt du démon...")
        self.is_running = False
        self.stop_event.set()
    
    def _shutdown(self):
        print("👋 CRYPTO BOT DAEMON ARRÊTÉ")
