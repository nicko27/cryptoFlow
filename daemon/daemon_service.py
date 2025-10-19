"""
Daemon Service - Exécution en arrière-plan avec gestion d'erreurs robuste
"""

import time
import signal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from threading import Event

from core.models import BotConfiguration, AlertLevel, MarketData, Prediction, OpportunityScore
from api.binance_api import BinanceAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from utils.logger import setup_logger
from core.services.database_service import DatabaseService
from core.services.chart_service import ChartService
from api.enhanced_telegram_api import EnhancedTelegramAPI
from core.services.report_service import ReportService
from core.services.dca_service import DCAService


class DaemonService:
    def __init__(self, config: BotConfiguration):
        self.config = config

        # État d'exécution
        self.is_running = False
        self.stop_event = Event()
        self.start_time: Optional[datetime] = None
        self.last_check_time: Optional[datetime] = None
        self.last_summary_sent: Optional[datetime] = None
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0
        self.consecutive_errors = 0
        self.last_error: Optional[str] = None

        # Logger
        self.logger = setup_logger(
            name="CryptoBotDaemon",
            log_file=config.log_file,
            level=config.log_level
        )

        # Services principaux
        self.binance_api = BinanceAPI()
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        self.db_service = DatabaseService(config.database_path)
        self.chart_service = ChartService()
        self.report_service = ReportService(config)
        self.dca_service = DCAService()
        self.telegram_api = EnhancedTelegramAPI(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message_delay=config.telegram_message_delay
        )

        # Gestion des signaux système
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def update_configuration(self, config: BotConfiguration) -> None:
        """Met à jour les services internes avec une nouvelle configuration."""
        self.config = config
        self.alert_service = AlertService(config)
        self.report_service.configure(config)
        self.telegram_api.message_delay = config.telegram_message_delay

    def _coin_option(self, symbol: str, key: str, default):
        """Récupère une option spécifique à une monnaie"""
        settings = getattr(self.config, "coin_settings", {}) or {}
        return settings.get(symbol, {}).get(key, default)

    def _coin_investment_amount(self, symbol: str) -> float:
        """Récupère le montant d'investissement pour une monnaie"""
        return float(self._coin_option(symbol, "investment_amount", self.config.investment_amount))

    def _check_cycle(self):
        """Exécute un cycle de vérification complet avec gestion d'erreurs robuste"""
        
        quiet_mode = False
        if self.config.enable_quiet_hours and self._is_quiet_hours():
            quiet_mode = True
            self.logger.info("🌙 Mode nuit actif - vérification silencieuse")
        
        self.checks_count += 1
        self.last_check_time = datetime.now(timezone.utc)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count}")
        self.logger.info(f"{'='*60}")
        
        cycle_errors = 0
        for symbol in self.config.crypto_symbols:
            try:
                self._process_symbol(symbol, quiet_mode)
                self.consecutive_errors = 0  # Reset sur succès
            except Exception as exc:
                self.logger.error(f"❌ Erreur vérification {symbol}: {exc}", exc_info=True)
                self.errors_count += 1
                cycle_errors += 1
                self.consecutive_errors += 1
                self.last_error = f"{symbol}: {str(exc)}"
                
                # Attendre un peu avant de continuer si erreur
                if cycle_errors < len(self.config.crypto_symbols):
                    time.sleep(2)
        
        # Résumés automatiques (hors mode nuit)
        if not quiet_mode and self.config.notification_per_coin:
            try:
                if self._should_send_summary():
                    self._send_auto_summary()
            except Exception as exc:
                self.logger.error(f"❌ Erreur envoi résumé auto: {exc}", exc_info=True)
        
        # Sauvegarder les stats
        try:
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
            
            self.db_service.save_stats(
                self.checks_count,
                self.alerts_sent,
                self.errors_count,
                uptime_seconds
            )
        except Exception as exc:
            self.logger.error(f"❌ Erreur sauvegarde stats: {exc}")
        
        # Afficher les stats
        if self.start_time:
            uptime = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
            self.logger.info(
                f"\n📊 Stats : {self.checks_count} vérifications, "
                f"{self.alerts_sent} alertes, {self.errors_count} erreurs "
                f"({self.consecutive_errors} consécutives), "
                f"Uptime: {uptime // 3600}h{(uptime % 3600) // 60}m"
            )
        
        # Nettoyage périodique
        if self.checks_count % 100 == 0:
            try:
                self.db_service.cleanup_old_data(self.config.keep_history_days)
                self.logger.info("🧹 Nettoyage base de données effectué")
            except Exception as exc:
                self.logger.error(f"❌ Erreur nettoyage DB: {exc}")

    def _process_symbol(self, symbol: str, quiet_mode: bool) -> None:
        """Analyse et traite une crypto avec gestion d'erreur par étape"""
        
        self.logger.info(f"\n📊 {symbol}:")
        self.logger.info("-" * 60)
        
        # Récupération données marché
        try:
            market_data = self.market_service.get_market_data(symbol)
            if not market_data:
                self.logger.warning(f"⚠️ Pas de données marché pour {symbol}")
                return
        except Exception as exc:
            self.logger.error(f"❌ Erreur récupération données {symbol}: {exc}")
            raise
        
        # Affichage prix
        try:
            self.logger.info(
                f"💰 Prix : {market_data.current_price.price_eur:.2f} € "
                f"({market_data.current_price.change_24h:+.2f}% 24h)"
            )
        except Exception as exc:
            self.logger.error(f"❌ Erreur affichage prix {symbol}: {exc}")
        
        # Prédiction
        prediction = None
        try:
            if self.config.enable_predictions:
                prediction = self.market_service.predict_price_movement(market_data)
                if prediction:
                    self.logger.info(
                        f"🔮 Prédiction : {prediction.prediction_type.value} "
                        f"({prediction.confidence:.0f}%)"
                    )
        except Exception as exc:
            self.logger.error(f"❌ Erreur prédiction {symbol}: {exc}")
        
        # Score d'opportunité
        opportunity = None
        try:
            if self.config.enable_opportunity_score:
                opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                if opportunity:
                    self.logger.info(f"⭐ Opportunité : {opportunity.score}/10")
        except Exception as exc:
            self.logger.error(f"❌ Erreur calcul opportunité {symbol}: {exc}")
        
        # Vérification alertes
        alerts = []
        try:
            if self.config.enable_alerts:
                alerts = self.alert_service.check_alerts(market_data, prediction)
                
                if alerts:
                    self.logger.info(f"🚨 {len(alerts)} alerte(s) générée(s)")
                    for alert in alerts:
                        self.logger.info(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                else:
                    self.logger.info("ℹ️ Aucune alerte")
        except Exception as exc:
            self.logger.error(f"❌ Erreur vérification alertes {symbol}: {exc}")
        
        # Envoi alertes Telegram (si pas en mode nuit ou si critique)
        if alerts and not quiet_mode:
            for alert in alerts:
                try:
                    if quiet_mode and not self.config.quiet_allow_critical:
                        if alert.alert_level != AlertLevel.CRITICAL:
                            continue
                    
                    sent = self.telegram_api.send_alert(alert, include_metadata=False)
                    if sent:
                        self.alerts_sent += 1
                        self.logger.info("   ✓ Alerte envoyée sur Telegram")
                    else:
                        self.logger.warning("   ⚠️ Échec envoi Telegram")
                except Exception as exc:
                    self.logger.error(f"   ❌ Erreur envoi Telegram : {exc}")
        
        # Notification individuelle par monnaie
        if self.config.notification_per_coin and not quiet_mode:
            try:
                notification = self.report_service.generate_coin_notification(
                    symbol, market_data, prediction, opportunity
                )
                if notification:
                    sent = self.telegram_api.send_message(notification, use_queue=True)
                    if sent:
                        self.logger.info("✓ Notification envoyée")
            except Exception as exc:
                self.logger.error(f"❌ Erreur notification {symbol}: {exc}")
        
        # Sauvegarde en base de données
        try:
            self.db_service.save_price(market_data.current_price)
            if prediction:
                self.db_service.save_prediction(prediction, market_data.symbol)
            for alert in alerts:
                self.db_service.save_alert(alert)
        except Exception as exc:
            self.logger.error(f"❌ Erreur sauvegarde DB {symbol}: {exc}")

    def _is_quiet_hours(self) -> bool:
        """Vérifie si on est en heures silencieuses"""
        current_hour = datetime.now().hour
        start = self.config.quiet_start_hour
        end = self.config.quiet_end_hour
        
        if start < end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end

    def _should_send_summary(self) -> bool:
        """Vérifie s'il faut envoyer un résumé"""
        if not self.config.summary_hours:
            return False
        
        current_hour = datetime.now().hour
        if current_hour not in self.config.summary_hours:
            return False
        
        # Éviter d'envoyer plusieurs fois la même heure
        if self.last_summary_sent:
            elapsed_hours = (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() / 3600
            if elapsed_hours < 1:
                return False
        
        return True

    def _send_auto_summary(self):
        """Envoie un résumé automatique avec gestion d'erreur"""
        try:
            self.logger.info("📊 Envoi résumé automatique...")
            
            markets_data: Dict[str, MarketData] = {}
            predictions: Dict[str, Prediction] = {}
            opportunities: Dict[str, OpportunityScore] = {}

            for symbol in self.config.crypto_symbols:
                try:
                    market = self.market_service.get_market_data(symbol, refresh=False)
                    if market:
                        markets_data[symbol] = market
                        
                        pred = self.market_service.predict_price_movement(market)
                        if pred:
                            predictions[symbol] = pred
                        
                        opp = self.market_service.calculate_opportunity_score(market, pred)
                        if opp:
                            opportunities[symbol] = opp
                except Exception as exc:
                    self.logger.error(f"❌ Erreur données résumé {symbol}: {exc}")

            # Envoyer notifications individuelles
            if self.config.notification_per_coin:
                for symbol in self.config.crypto_symbols:
                    try:
                        notification = self.report_service.generate_coin_notification(
                            symbol,
                            markets_data.get(symbol),
                            predictions.get(symbol),
                            opportunities.get(symbol)
                        )
                        if notification:
                            self.telegram_api.send_message(notification, use_queue=True)
                    except Exception as exc:
                        self.logger.error(f"❌ Erreur notification résumé {symbol}: {exc}")

            self.last_summary_sent = datetime.now(timezone.utc)
            self.logger.info("✓ Résumé envoyé")

        except Exception as e:
            self.logger.error(f"❌ Erreur résumé automatique : {e}", exc_info=True)

    def _test_telegram(self) -> bool:
        """Test la connexion Telegram"""
        try:
            self.logger.info("🔍 Test de connexion Telegram...")
            
            # Test simple
            info = self.telegram_api.test_connection()
            if info:
                bot_name = info.get('username', 'Bot')
                self.logger.info(f"✓ Connecté au bot: @{bot_name}")
                return True
            else:
                self.logger.error("❌ Échec test connexion")
                return False
        except Exception as e:
            self.logger.error(f"❌ Erreur test Telegram : {e}")
            return False

    def _send_startup_message(self):
        """Envoie le message de démarrage avec état initial"""
        try:
            self.logger.info("📊 Récupération état initial du marché...")
            
            summary_data: Dict[str, Dict[str, Any]] = {}
            markets: Dict[str, MarketData] = {}
            predictions: Dict[str, Prediction] = {}
            opportunities: Dict[str, OpportunityScore] = {}

            for symbol in self.config.crypto_symbols:
                try:
                    market = self.market_service.get_market_data(symbol)
                    if not market:
                        continue
                    
                    markets[symbol] = market
                    pred = self.market_service.predict_price_movement(market)
                    predictions[symbol] = pred
                    
                    opp = self.market_service.calculate_opportunity_score(market, pred)
                    opportunities[symbol] = opp
                    
                    summary_data[symbol] = {
                        'market': market,
                        'prediction': pred,
                        'opportunity': opp
                    }
                    
                    price = market.current_price.price_eur
                    change = market.current_price.change_24h
                    recommendation = opp.recommendation if opp else "Analyser"
                    
                    self.logger.info(f"  • {symbol}: {price:.2f}€ - {recommendation}")
                    
                except Exception as exc:
                    self.logger.error(f"❌ Erreur init {symbol}: {exc}")

            # Message d'en-tête
            header_lines = [
                "🚀 <b>Crypto Bot Démarré</b>",
                "",
                f"📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                f"🔄 Vérification toutes les {self.config.check_interval_seconds // 60} minutes",
            ]

            if self.config.enable_alerts:
                header_lines.append(
                    f"🔔 Alertes prix actives (−{self.config.price_drop_threshold}% / +{self.config.price_spike_threshold}%)"
                )
            
            if self.config.notification_per_coin:
                header_lines.append("💬 Notifications individuelles activées")
            
            if self.config.enable_quiet_hours:
                header_lines.append(
                    f"🌙 Mode nuit : {self.config.quiet_start_hour}h → {self.config.quiet_end_hour}h"
                )

            self.telegram_api.send_message("\n".join(header_lines), use_queue=False)
            self.logger.info("✓ Message de démarrage envoyé sur Telegram")

            # Notifications individuelles par monnaie
            for symbol in self.config.crypto_symbols:
                try:
                    notification = self.report_service.generate_coin_notification(
                        symbol,
                        markets.get(symbol),
                        predictions.get(symbol),
                        opportunities.get(symbol),
                    )
                    if notification:
                        self.telegram_api.send_message(notification, use_queue=False)
                        time.sleep(1)
                except Exception as exc:
                    self.logger.error(f"❌ Erreur notification démarrage {symbol}: {exc}")

        except Exception as e:
            self.logger.error(f"❌ Erreur message de démarrage : {e}", exc_info=True)

    def _signal_handler(self, signum, frame):
        """Handler pour signaux système"""
        self.logger.info(f"⚡ Signal {signum} reçu, arrêt du démon...")
        self.stop()
    
    def start(self):
        """Démarre le service démon"""
        if self.is_running:
            self.logger.warning("⚠️ Le démon est déjà en cours d'exécution")
            return

        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            self.logger.error("❌ Configuration Telegram invalide")
            return

        self.stop_event.clear()
        self.is_running = True
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0
        self.consecutive_errors = 0
        self.start_time = datetime.now(timezone.utc)

        # Démarrer la queue Telegram
        self.telegram_api.start_queue()
        
        self.logger.info("="*60)
        self.logger.info("🚀 CRYPTO BOT DAEMON DÉMARRÉ")
        self.logger.info("="*60)
        self.logger.info(f"Cryptos surveillées : {', '.join(self.config.crypto_symbols)}")
        self.logger.info(f"Intervalle : {self.config.check_interval_seconds}s")
        self.logger.info(f"Mode nuit : {'Activé' if self.config.enable_quiet_hours else 'Désactivé'}")
        self.logger.info("="*60)
        
        # Test connexion Telegram
        if not self._test_telegram():
            self.logger.error("❌ Connexion Telegram échouée !")
            self.stop()
            return
        
        # Message de démarrage
        if self.config.enable_startup_summary:
            self._send_startup_message()
        
        # Boucle principale avec gestion d'erreurs robuste
        self._run_loop()
    
    def _run_loop(self):
        """Boucle principale du démon avec retry automatique"""
        retry_delay = 60  # Délai avant retry après erreur
        
        while self.is_running and not self.stop_event.is_set():
            try:
                self._check_cycle()
                
                # Si trop d'erreurs consécutives, augmenter le délai
                if self.consecutive_errors > 20:
                    self.logger.critical(f"❌ Trop d'erreurs consécutives ({self.consecutive_errors}), pause longue")
                    wait_time = self.config.check_interval_seconds * 2
                elif self.consecutive_errors > 10:
                    self.logger.warning(f"⚠️ {self.consecutive_errors} erreurs consécutives, pause augmentée")
                    wait_time = self.config.check_interval_seconds * 1.5
                else:
                    wait_time = self.config.check_interval_seconds
                
                # Attendre prochain cycle
                self.stop_event.wait(timeout=wait_time)
            
            except KeyboardInterrupt:
                self.logger.info("⌨️ Interruption clavier détectée")
                break
            
            except Exception as e:
                self.logger.error(f"❌ Erreur critique dans boucle principale : {e}", exc_info=True)
                self.errors_count += 1
                self.consecutive_errors += 1
                self.last_error = str(e)
                
                if self.consecutive_errors > 30:
                    self.logger.critical("❌ Trop d'erreurs critiques, arrêt du démon")
                    break
                
                # Attendre avant de réessayer
                self.logger.info(f"⏳ Retry dans {retry_delay}s...")
                time.sleep(retry_delay)
        
        # Arrêt propre
        self._shutdown()
    
    def stop(self):
        """Arrête le démon"""
        self.logger.info("\n🛑 Arrêt du démon demandé...")
        self.is_running = False
        self.stop_event.set()
    
    def _shutdown(self):
        """Nettoyage avant arrêt"""
        self.is_running = False
        self.stop_event.set()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("👋 CRYPTO BOT DAEMON ARRÊTÉ")
        self.logger.info("="*60)
        
        uptime = 0
        if self.start_time:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            self.logger.info(f"Uptime : {int(uptime/3600)}h {int((uptime%3600)/60)}m")
        
        self.logger.info(f"Vérifications : {self.checks_count}")
        self.logger.info(f"Alertes envoyées : {self.alerts_sent}")
        self.logger.info(f"Erreurs : {self.errors_count}")
        self.logger.info("="*60 + "\n")
        
        # Arrêter la queue Telegram
        try:
            self.telegram_api.stop_queue()
        except Exception:
            pass

        # Message Telegram d'arrêt
        try:
            uptime_str = f"{int(uptime/3600)}h{int((uptime%3600)/60)}m" if self.start_time else "N/A"
            message = "🛑 <b>Crypto Bot Arrêté</b>\n\n"
            message += f"📊 <b>Statistiques:</b>\n"
            message += f"  • Vérifications : {self.checks_count}\n"
            message += f"  • Alertes envoyées : {self.alerts_sent}\n"
            message += f"  • Erreurs : {self.errors_count}\n"
            message += f"  • Uptime : {uptime_str}\n\n"
            message += "👋 À bientôt !"

            self.telegram_api.send_message(message)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état actuel du daemon"""
        return {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "last_check_time": self.last_check_time,
            "last_summary_sent": self.last_summary_sent,
            "checks_count": self.checks_count,
            "alerts_sent": self.alerts_sent,
            "errors_count": self.errors_count,
            "consecutive_errors": self.consecutive_errors,
            "last_error": self.last_error,
            "uptime_seconds": int((datetime.now(timezone.utc) - self.start_time).total_seconds()) if self.start_time else 0,
            "queue": {
                "queue_size": len(self.telegram_api.message_queue) if hasattr(self.telegram_api, 'message_queue') else 0
            }
        }


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
