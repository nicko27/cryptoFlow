"""
Daemon Service - Exécution en arrière-plan
"""

import time
import signal
import sys
from datetime import datetime
from typing import Optional
from threading import Event

from core.models import BotConfiguration
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from utils.logger import setup_logger


class DaemonService:
    """Service pour exécution en mode démon"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.is_running = False
        self.stop_event = Event()
        
        # Logger
        self.logger = setup_logger(
            name="CryptoBotDaemon",
            log_file=config.log_file,
            level=config.log_level
        )
        
        # Services
        self.binance_api = BinanceAPI()
        self.telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        
        # Stats
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0
        self.start_time: Optional[datetime] = None
        
        # Enregistrer handler signaux
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler pour signaux système"""
        self.logger.info(f"Signal {signum} reçu, arrêt du démon...")
        self.stop()
    
    def start(self):
        """Démarre le service démon"""
        if self.is_running:
            self.logger.warning("Le démon est déjà en cours d'exécution")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        self.logger.info("="*60)
        self.logger.info("🚀 CRYPTO BOT DAEMON DÉMARRÉ")
        self.logger.info("="*60)
        self.logger.info(f"Cryptos surveillées : {', '.join(self.config.crypto_symbols)}")
        self.logger.info(f"Intervalle : {self.config.check_interval_seconds}s")
        self.logger.info(f"Mode nuit : {'Activé' if self.config.enable_quiet_hours else 'Désactivé'}")
        self.logger.info("="*60)
        
        # Test connexion Telegram
        if not self._test_telegram():
            self.logger.error("❌ Connexion Telegram échouée ! Vérifiez votre configuration.")
            return
        
        # Envoyer message de démarrage
        if self.config.enable_startup_summary:
            self._send_startup_message()
        
        # Boucle principale
        try:
            self._run_loop()
        except Exception as e:
            self.logger.error(f"Erreur fatale : {e}", exc_info=True)
        finally:
            self._shutdown()
    
    def _test_telegram(self) -> bool:
        """Teste la connexion Telegram"""
        try:
            return self.telegram_api.test_connection()
        except Exception as e:
            self.logger.error(f"Erreur test Telegram : {e}")
            return False
    
    def _send_startup_message(self):
        """Envoie un message de démarrage"""
        try:
            message = "🚀 <b>Crypto Bot Démarré</b>\n\n"
            message += f"Cryptos : {', '.join(self.config.crypto_symbols)}\n"
            message += f"Intervalle : {self.config.check_interval_seconds}s\n"
            message += f"Démarrage : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            
            self.telegram_api.send_message(message)
        except Exception as e:
            self.logger.error(f"Erreur envoi message démarrage : {e}")
    
    def _run_loop(self):
        """Boucle principale du démon"""
        while self.is_running and not self.stop_event.is_set():
            try:
                self._check_cycle()
                
                # Attendre prochain cycle
                self.stop_event.wait(timeout=self.config.check_interval_seconds)
            
            except KeyboardInterrupt:
                self.logger.info("Interruption clavier détectée")
                break
            
            except Exception as e:
                self.logger.error(f"Erreur dans boucle principale : {e}", exc_info=True)
                self.errors_count += 1
                
                # Si trop d'erreurs, arrêter
                if self.errors_count > 10:
                    self.logger.critical("Trop d'erreurs consécutives, arrêt du démon")
                    break
                
                # Attendre avant de réessayer
                time.sleep(60)
    
    def _check_cycle(self):
        """Un cycle de vérification complet"""
        self.checks_count += 1
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count}")
        self.logger.info(f"{'='*60}")
        
        for symbol in self.config.crypto_symbols:
            try:
                self._check_crypto(symbol)
            except Exception as e:
                self.logger.error(f"Erreur vérification {symbol} : {e}", exc_info=True)
                self.errors_count += 1
        
        # Log stats
        uptime = (datetime.now() - self.start_time).total_seconds()
        self.logger.info(f"\n📊 Stats : {self.checks_count} vérifications, "
                        f"{self.alerts_sent} alertes, {self.errors_count} erreurs, "
                        f"Uptime: {int(uptime/3600)}h{int((uptime%3600)/60)}m")
    
    def _check_crypto(self, symbol: str):
        """Vérifie une crypto"""
        self.logger.info(f"\n📊 {symbol}:")
        self.logger.info("-" * 60)
        
        # Récupérer données de marché
        market_data = self.market_service.get_market_data(symbol)
        if not market_data:
            self.logger.warning(f"Impossible de récupérer les données pour {symbol}")
            return
        
        price = market_data.current_price.price_eur
        change_24h = market_data.current_price.change_24h
        
        self.logger.info(f"💰 Prix : {price:.2f} € ({change_24h:+.2f}% 24h)")
        
        # Prédiction
        prediction = self.market_service.predict_price_movement(market_data)
        self.logger.info(f"🔮 Prédiction : {prediction.prediction_type.value} "
                        f"({prediction.confidence}%)")
        
        # Score opportunité
        opportunity = self.market_service.calculate_opportunity_score(
            market_data, prediction
        )
        self.logger.info(f"⭐ Opportunité : {opportunity.score}/10")
        
        # Vérifier alertes
        alerts = self.alert_service.check_alerts(market_data, prediction)
        
        if alerts:
            self.logger.info(f"🚨 {len(alerts)} alerte(s) générée(s)")
            
            for alert in alerts:
                self.logger.info(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                
                # Envoyer alertes importantes sur Telegram
                if alert.alert_level.value in ["important", "critical"]:
                    try:
                        success = self.telegram_api.send_alert(alert, include_metadata=True)
                        if success:
                            self.alerts_sent += 1
                            self.logger.info(f"   ✓ Alerte envoyée sur Telegram")
                        else:
                            self.logger.warning(f"   ✗ Échec envoi Telegram")
                    except Exception as e:
                        self.logger.error(f"   ✗ Erreur envoi Telegram : {e}")
        else:
            self.logger.info("ℹ️ Aucune alerte")
    
    def stop(self):
        """Arrête le démon"""
        self.logger.info("\n🛑 Arrêt du démon demandé...")
        self.is_running = False
        self.stop_event.set()
    
    def _shutdown(self):
        """Nettoyage avant arrêt"""
        self.logger.info("\n" + "="*60)
        self.logger.info("👋 CRYPTO BOT DAEMON ARRÊTÉ")
        self.logger.info("="*60)
        
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"Uptime : {int(uptime/3600)}h {int((uptime%3600)/60)}m")
        
        self.logger.info(f"Vérifications : {self.checks_count}")
        self.logger.info(f"Alertes envoyées : {self.alerts_sent}")
        self.logger.info(f"Erreurs : {self.errors_count}")
        self.logger.info("="*60 + "\n")
        
        # Message Telegram
        try:
            uptime_str = f"{int(uptime/3600)}h{int((uptime%3600)/60)}m" if self.start_time else "N/A"
            message = "🛑 <b>Crypto Bot Arrêté</b>\n\n"
            message += f"Vérifications : {self.checks_count}\n"
            message += f"Alertes : {self.alerts_sent}\n"
            message += f"Uptime : {uptime_str}\n"
            
            self.telegram_api.send_message(message)
        except:
            pass


def main():
    """Test du daemon"""
    from core.models import BotConfiguration
    
    config = BotConfiguration()
    config.crypto_symbols = ["BTC", "ETH"]
    config.check_interval_seconds = 60  # 1 minute pour test
    
    daemon = DaemonService(config)
    
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
