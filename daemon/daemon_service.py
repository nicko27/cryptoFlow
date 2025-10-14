"""
Daemon Service - Exécution en arrière-plan [FIXED]
"""

import time
import signal
import sys
from datetime import datetime
from typing import Optional
from threading import Event

from core.models import BotConfiguration, AlertLevel, now_utc
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from utils.logger import setup_colored_logger
import logging

logger = logging.getLogger("CryptoBot.Daemon")


class DaemonService:
    """Service pour exécution en mode démon avec gestion d'erreurs robuste"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.is_running = False
        self.stop_event = Event()
        
        # Services
        self.binance_api = BinanceAPI()
        self.telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        
        # Stats
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0
        self.consecutive_errors = 0
        self.start_time: Optional[datetime] = None
        
        # Enregistrer handler signaux
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler pour signaux système"""
        logger.info(f"Signal {signum} reçu, arrêt du démon...")
        self.stop()
    
    def start(self):
        """Démarre le service démon"""
        if self.is_running:
            logger.warning("Le démon est déjà en cours d'exécution")
            return
        
        self.is_running = True
        self.start_time = now_utc()
        
        logger.info("="*60)
        logger.info("🚀 CRYPTO BOT DAEMON DÉMARRÉ")
        logger.info("="*60)
        logger.info(f"Cryptos surveillées : {', '.join(self.config.crypto_symbols)}")
        logger.info(f"Intervalle : {self.config.check_interval_seconds}s")
        logger.info(f"Mode nuit : {'Activé' if self.config.enable_quiet_hours else 'Désactivé'}")
        logger.info("="*60)
        
        # Test connexion Telegram
        if not self._test_telegram():
            logger.error("❌ Connexion Telegram échouée ! Vérifiez votre configuration.")
            logger.error("Le bot continuera mais les alertes ne seront pas envoyées.")
        
        # Envoyer message de démarrage
        if self.config.enable_startup_summary:
            self._send_startup_message()
        
        # Boucle principale
        try:
            self._run_loop()
        except Exception as e:
            logger.error(f"Erreur fatale : {e}", exc_info=True)
        finally:
            self._shutdown()
    
    def _test_telegram(self) -> bool:
        """Teste la connexion Telegram"""
        try:
            return self.telegram_api.test_connection()
        except Exception as e:
            logger.error(f"Erreur test Telegram : {e}", exc_info=True)
            return False
    
    def _send_startup_message(self):
        """Envoie un message de démarrage"""
        try:
            message = "🚀 <b>Crypto Bot Démarré</b>\n\n"
            message += f"Cryptos : {', '.join(self.config.crypto_symbols)}\n"
            message += f"Intervalle : {self.config.check_interval_seconds}s\n"
            message += f"Démarrage : {now_utc().strftime('%d/%m/%Y %H:%M')}\n"
            
            self.telegram_api.send_message(message)
        except Exception as e:
            logger.error(f"Erreur envoi message démarrage : {e}")
    
    def _run_loop(self):
        """Boucle principale du démon"""
        while self.is_running and not self.stop_event.is_set():
            try:
                self._check_cycle()
                
                # Reset compteur erreurs consécutives si succès
                self.consecutive_errors = 0
                
                # Attendre prochain cycle
                self.stop_event.wait(timeout=self.config.check_interval_seconds)
            
            except KeyboardInterrupt:
                logger.info("Interruption clavier détectée")
                break
            
            except Exception as e:
                logger.error(f"Erreur dans boucle principale : {e}", exc_info=True)
                self.errors_count += 1
                self.consecutive_errors += 1
                
                # Si trop d'erreurs consécutives, augmenter le délai
                if self.consecutive_errors > 5:
                    logger.critical("Trop d'erreurs consécutives, pause de 5 minutes")
                    self.stop_event.wait(timeout=300)
                
                # Si vraiment trop d'erreurs, arrêter
                if self.consecutive_errors > 10:
                    logger.critical("Trop d'erreurs consécutives, arrêt du démon")
                    break
                
                # Attendre avant de réessayer
                self.stop_event.wait(timeout=60)
    
    def _check_cycle(self):
        """Un cycle de vérification complet"""
        self.checks_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 VÉRIFICATION #{self.checks_count}")
        logger.info(f"{'='*60}")
        
        for symbol in self.config.crypto_symbols:
            if not self.is_running or self.stop_event.is_set():
                break
            
            try:
                self._check_crypto(symbol)
            except Exception as e:
                logger.error(f"Erreur vérification {symbol} : {e}", exc_info=True)
                self.errors_count += 1
        
        # Log stats
        if self.start_time:
            uptime = (now_utc() - self.start_time).total_seconds()
            logger.info(f"\n📊 Stats : {self.checks_count} vérifications, "
                       f"{self.alerts_sent} alertes, {self.errors_count} erreurs, "
                       f"Uptime: {int(uptime/3600)}h{int((uptime%3600)/60)}m")
    
    def _check_crypto(self, symbol: str):
        """Vérifie une crypto"""
        logger.info(f"\n📊 {symbol}:")
        logger.info("-" * 60)
        
        # Récupérer données de marché
        market_data = self.market_service.get_market_data(symbol)
        if not market_data:
            logger.warning(f"Impossible de récupérer les données pour {symbol}")
            return
        
        price = market_data.current_price.price_eur
        change_24h = market_data.current_price.change_24h
        
        logger.info(f"💰 Prix : {price:.2f} € ({change_24h:+.2f}% 24h)")
        
        # Prédiction
        prediction = self.market_service.predict_price_movement(market_data)
        logger.info(f"🔮 Prédiction : {prediction.prediction_type.value} "
                   f"({prediction.confidence}%)")
        
        # Score opportunité
        opportunity = self.market_service.calculate_opportunity_score(
            market_data, prediction
        )
        logger.info(f"⭐ Opportunité : {opportunity.score}/10")
        
        # Vérifier alertes
        alerts = self.alert_service.check_alerts(market_data, prediction)
        
        if alerts:
            logger.info(f"🚨 {len(alerts)} alerte(s) générée(s)")
            
            for alert in alerts:
                logger.info(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                
                # Envoyer alertes importantes sur Telegram
                if alert.alert_level.value in ["important", "critical"]:
                    try:
                        success = self.telegram_api.send_alert(alert, include_metadata=True)
                        if success:
                            self.alerts_sent += 1
                            logger.info(f"   ✓ Alerte envoyée sur Telegram")
                        else:
                            logger.warning(f"   ✗ Échec envoi Telegram")
                    except Exception as e:
                        logger.error(f"   ✗ Erreur envoi Telegram : {e}")
        else:
            logger.info("ℹ️ Aucune alerte")
    
    def stop(self):
        """Arrête le démon"""
        logger.info("\n🛑 Arrêt du démon demandé...")
        self.is_running = False
        self.stop_event.set()
    
    def _shutdown(self):
        """Nettoyage avant arrêt"""
        logger.info("\n" + "="*60)
        logger.info("👋 CRYPTO BOT DAEMON ARRÊTÉ")
        logger.info("="*60)
        
        if self.start_time:
            uptime = (now_utc() - self.start_time).total_seconds()
            logger.info(f"Uptime : {int(uptime/3600)}h {int((uptime%3600)/60)}m")
        
        logger.info(f"Vérifications : {self.checks_count}")
        logger.info(f"Alertes envoyées : {self.alerts_sent}")
        logger.info(f"Erreurs : {self.errors_count}")
        
        # Stats API
        api_stats = self.binance_api.get_api_stats()
        logger.info(f"API Binance : {api_stats['api_calls']} appels")
        
        telegram_stats = self.telegram_api.get_stats()
        logger.info(f"API Telegram : {telegram_stats['messages_sent']} messages, {telegram_stats['errors']} erreurs")
        
        logger.info("="*60 + "\n")
        
        # Message Telegram
        try:
            if self.start_time:
                uptime_str = f"{int(uptime/3600)}h{int((uptime%3600)/60)}m"
            else:
                uptime_str = "N/A"
            
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
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    
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
