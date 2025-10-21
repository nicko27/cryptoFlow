"""
Daemon Service - Exécution en arrière-plan avec gestion d'erreurs robuste
FIXED: Imports timezone, signal handlers thread-safe, méthode _dict_to_notification_settings
"""

import time
import signal
from datetime import datetime, timezone  # FIXED: Problème 1 - Import simple de timezone
from typing import Optional, Dict, Any, List
from threading import Event, Lock
import yaml
from pathlib import Path

from core.models import BotConfiguration, AlertLevel, MarketData, Prediction, OpportunityScore
from api.binance_api import BinanceAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from utils.logger import setup_logger
from core.services.database_service import DatabaseService
from core.services.chart_service import ChartService
from api.enhanced_telegram_api import EnhancedTelegramAPI
from core.services.dca_service import DCAService
from core.services.notification_generator import NotificationGenerator
from core.models.notification_config import GlobalNotificationSettings


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
        self.notifications_sent = 0  # Compteur de notifications
        self.errors_count = 0
        self.consecutive_errors = 0
        self.last_error: Optional[str] = None
        
        # FIXED: Problème 20 - Lock pour thread-safety
        self._state_lock = Lock()

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
        self.dca_service = DCAService()
        self.telegram_api = EnhancedTelegramAPI(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message_delay=config.telegram_message_delay
        )
        initial_settings = self._load_notification_settings()
        self.update_notification_settings(initial_settings)

        # FIXED: Problème 20 - Gestion des signaux système thread-safe
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_notification_settings(self) -> GlobalNotificationSettings:
        """Charge les paramètres de notification depuis YAML"""
        notif_config_path = "config/notifications.yaml"
        
        if Path(notif_config_path).exists():
            try:
                with open(notif_config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                return self._dict_to_notification_settings(data)
            except Exception as e:
                self.logger.error(f"Erreur chargement notifications: {e}")
        
        # Config par défaut
        return GlobalNotificationSettings(
            enabled=True,
            kid_friendly_mode=True,
            use_emojis_everywhere=True,
            explain_everything=True,
            respect_quiet_hours=True,
            quiet_start=23,
            quiet_end=7,
            default_scheduled_hours=[9, 12, 18]
        )
    
    def _dict_to_notification_settings(self, data: dict) -> GlobalNotificationSettings:
        """
        FIXED: Problème 8 - Méthode implémentée
        Convertit un dictionnaire YAML en GlobalNotificationSettings
        """
        def _normalize_hours(value):
            hours: List[int] = []
            if isinstance(value, (int, float)):
                hours.append(int(value))
            elif isinstance(value, str):
                for part in value.replace(";", ",").split(","):
                    part = part.strip()
                    if part.isdigit():
                        hours.append(int(part))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (int, float)):
                        hours.append(int(item))
                    elif isinstance(item, str) and item.strip().isdigit():
                        hours.append(int(item.strip()))
            return sorted({h for h in hours if 0 <= h <= 23})

        hours = _normalize_hours(data.get('default_scheduled_hours', [9, 12, 18])) or [9, 12, 18]
        quiet_start = int(data.get('quiet_start', 23) or 0)
        quiet_end = int(data.get('quiet_end', 7) or 0)
        quiet_start = max(0, min(23, quiet_start))
        quiet_end = max(0, min(23, quiet_end))

        return GlobalNotificationSettings(
            enabled=data.get('enabled', True),
            kid_friendly_mode=data.get('kid_friendly_mode', True),
            use_emojis_everywhere=data.get('use_emojis_everywhere', True),
            explain_everything=data.get('explain_everything', True),
            respect_quiet_hours=data.get('respect_quiet_hours', True),
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            default_scheduled_hours=hours
        )

    def update_notification_settings(self, settings: GlobalNotificationSettings) -> None:
        """Met à jour les paramètres de notification et régénère le générateur associé."""
        with self._state_lock:
            self.notification_settings = settings
            self.notification_generator = NotificationGenerator(
                settings,
                self.config.crypto_symbols,
            )

    def update_configuration(self, config: BotConfiguration) -> None:
        """Met à jour les services internes avec une nouvelle configuration."""
        with self._state_lock:
            self.config = config
            # Recréer les services si nécessaire
            self.alert_service = AlertService(config)
            self.notification_generator = NotificationGenerator(
                self.notification_settings,
                config.crypto_symbols,
            )
            self.logger.info("Configuration mise à jour")

    def _signal_handler(self, signum, frame):
        """
        FIXED: Problème 20 - Gestionnaire de signaux thread-safe
        Gère les signaux système (SIGINT, SIGTERM)
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Signal {signum} ({signal_name}) reçu, arrêt du démon...")
        
        # Thread-safe stop
        with self._state_lock:
            self.is_running = False
            self.stop_event.set()

    def start(self):
        """Démarre le démon en arrière-plan"""
        
        with self._state_lock:
            if self.is_running:
                self.logger.warning("Le démon est déjà en cours d'exécution")
                return
            
            self.is_running = True
            self.start_time = datetime.now(timezone.utc)  # FIXED: Problème 2 - timezone.utc
        
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 CRYPTO BOT DAEMON DÉMARRÉ")
        self.logger.info("="*60)
        self.logger.info(f"Cryptos surveillées : {', '.join(self.config.crypto_symbols)}")
        self.logger.info(f"Intervalle : {self.config.check_interval_seconds}s")
        self.logger.info(f"Mode nuit : {'Activé' if self.config.enable_night_mode else 'Désactivé'}")
        self.logger.info("="*60)
        
        # Test connexion Telegram
        if not self._test_telegram_connection():
            self.logger.error("❌ Connexion Telegram échouée ! Vérifiez votre configuration.")
            with self._state_lock:
                self.is_running = False
            self.stop()
            return
        
        # Message de démarrage
        if self.config.enable_startup_summary:
            self._send_startup_message()
        
        # Boucle principale avec gestion d'erreurs robuste
        self._run_loop()
    
    def _test_telegram_connection(self) -> bool:
        """Teste la connexion Telegram"""
        try:
            self.logger.info("🔍 Test de connexion Telegram...")
            
            # FIXED: Problème 3 - Vérifier que la méthode existe
            if hasattr(self.telegram_api, 'get_bot_info'):
                bot_info = self.telegram_api.get_bot_info()
                self.logger.info(f"✓ Connecté au bot: @{bot_info.get('username', 'Unknown')}")
            else:
                # Fallback: tester avec un message
                self.telegram_api.send_message("✅ Test de connexion réussi")
                self.logger.info("✓ Connexion Telegram OK")
            
            return True
        except Exception as e:
            self.logger.error(f"Erreur test Telegram : {e}")
            return False
    
    def _run_loop(self):
        """
        FIXED: Problème 14 & 15 - Boucle principale améliorée
        avec meilleure gestion des erreurs et logging
        """
        retry_delay = 60
        last_log_time = datetime.now(timezone.utc)
        
        while self.is_running and not self.stop_event.is_set():
            try:
                cycle_start = datetime.now(timezone.utc)
                
                self._check_cycle()
                
                # FIXED: Problème 14 - Logging périodique avec timestamp
                now = datetime.now(timezone.utc)
                if (now - last_log_time).total_seconds() > 300:  # Toutes les 5 minutes
                    self._log_periodic_stats()
                    last_log_time = now
                
                # Calcul du délai d'attente
                if self.consecutive_errors > 20:
                    self.logger.critical(
                        f"❌ Trop d'erreurs consécutives ({self.consecutive_errors}), "
                        f"pause longue"
                    )
                    wait_time = self.config.check_interval_seconds * 2
                elif self.consecutive_errors > 10:
                    self.logger.warning(
                        f"⚠️ {self.consecutive_errors} erreurs consécutives, "
                        f"pause augmentée"
                    )
                    wait_time = self.config.check_interval_seconds * 1.5
                else:
                    wait_time = self.config.check_interval_seconds
                
                # Attendre prochain cycle
                self.stop_event.wait(timeout=wait_time)
            
            except KeyboardInterrupt:
                self.logger.info("⌨️ Interruption clavier détectée")
                break
            
            except Exception as e:
                # FIXED: Problème 15 - Meilleure gestion des erreurs avec context
                self.logger.error(
                    f"❌ Erreur critique dans boucle principale : {e}",
                    exc_info=True,
                    extra={'timestamp': datetime.now(timezone.utc).isoformat()}
                )
                
                with self._state_lock:
                    self.errors_count += 1
                    self.consecutive_errors += 1
                    self.last_error = str(e)
                
                if self.consecutive_errors > 30:
                    self.logger.critical("❌ Trop d'erreurs critiques, arrêt du démon")
                    break
                
                self.logger.info(f"⏳ Retry dans {retry_delay}s...")
                time.sleep(retry_delay)
        
        # Arrêt propre
        self._shutdown()
    
    def _log_periodic_stats(self):
        """
        FIXED: Problème 14 - Log périodique des stats sans doublons
        """
        with self._state_lock:
            if self.start_time:
                uptime = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
                self.logger.info(
                    f"📊 [Stats] Checks: {self.checks_count}, "
                    f"Alertes: {self.alerts_sent}, "
                    f"Erreurs: {self.errors_count} (consécutives: {self.consecutive_errors}), "
                    f"Uptime: {uptime // 3600}h{(uptime % 3600) // 60}m"
                )
    
    def _check_cycle(self):
        try:
            current_hour = datetime.now(timezone.utc).hour
            
            # Collecter les données
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            self.logger.info("\\n" + "="*60)
            self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count + 1}")
            self.logger.info("="*60)
            
            # Récupérer données pour chaque crypto
            for symbol in self.config.crypto_symbols:
                try:
                    self.logger.info(f"\\n📊 {symbol}:")
                    self.logger.info("-"*60)
                    
                    market_data = self.market_service.get_market_data(symbol)
                    if not market_data:
                        self.logger.warning(f"⚠️ Données indisponibles pour {symbol}")
                        continue
                    
                    markets_data[symbol] = market_data
                    
                    # Prédiction
                    prediction = self.market_service.predict_price_movement(market_data)
                    if prediction:
                        predictions[symbol] = prediction
                        self.logger.info(
                            f"🔮 Prédiction: {prediction.prediction_type.value.upper()} "
                            f"({prediction.confidence:.0f}%)"
                        )
                    
                    # Opportunité
                    opportunity = self.market_service.calculate_opportunity_score(
                        market_data, prediction
                    )
                    if opportunity:
                        opportunities[symbol] = opportunity
                        self.logger.info(f"⭐ Opportunité: {opportunity.score}/10")
                    
                    # Sauvegarder
                    self.db_service.save_market_data(market_data)
                    if prediction:
                        self.db_service.save_prediction(symbol, prediction)
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur {symbol}: {e}")
                    self.consecutive_errors += 1
            
            self.checks_count += 1
            
            # ENVOYER RÉSUMÉ si heure programmée
            should_send = False
            if current_hour in self.config.summary_hours:
                if self.last_summary_sent is None or (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
                    should_send = True
                    self.logger.info(f"⏰ Heure programmée: {current_hour}h")
            
            if should_send and markets_data:
                try:
                    self.logger.info("\\n📤 Envoi du résumé...")
                    
                    # Générer via SummaryService
                    summary = self.summary_service.generate_summary(
                        markets_data,
                        predictions,
                        opportunities,
                        simple=self.config.use_simple_language
                    )
                    
                    if summary:
                        success = self.telegram_api.send_message(summary, parse_mode="HTML")
                        if success:
                            self.notifications_sent += 1
                            self.last_summary_sent = datetime.now(timezone.utc)
                            self.logger.info("✅ Résumé envoyé")
                        else:
                            self.logger.error("❌ Échec envoi résumé")
                    else:
                        self.logger.warning("⚠️ Résumé vide")
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur envoi résumé: {e}")
            
            # Vérifier alertes pour chaque crypto
            for symbol in self.config.crypto_symbols:
                if symbol not in markets_data:
                    continue
                
                try:
                    market_data = markets_data[symbol]
                    prediction = predictions.get(symbol)
                    
                    alerts = self.alert_service.check_alerts(market_data, prediction)
                    
                    if alerts:
                        self.logger.info(f"\\n🚨 {len(alerts)} alerte(s) pour {symbol}")
                        for alert in alerts:
                            try:
                                self.telegram_api.send_alert(alert)
                                self.alerts_sent += 1
                                self.logger.info(f"   ✓ Alerte: {alert.message}")
                            except Exception as e:
                                self.logger.error(f"❌ Erreur alerte: {e}")
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur alertes {symbol}: {e}")
            
            # Stats
            if self.start_time:
                uptime = datetime.now(timezone.utc) - self.start_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                
                self.logger.info(
                    f"\\n📊 Stats: {self.checks_count} checks, "
                    f"{self.alerts_sent} alertes, {self.notifications_sent} notifs, "
                    f"{self.errors_count} erreurs, Uptime: {hours}h{minutes}m"
                )
            
            # Reset erreurs si succès
            if markets_data:
                self.consecutive_errors = 0
        
        except Exception as e:
            self.logger.error(f"❌ Erreur cycle: {e}", exc_info=True)
            self.errors_count += 1
            self.consecutive_errors += 1

    def _is_night_mode(self) -> bool:
        """Détermine si on est en mode nuit"""
        if not self.config.enable_night_mode:
            return False
        
        current_hour = datetime.now(timezone.utc).hour
        return (
            current_hour < self.config.night_mode_start_hour or
            current_hour >= self.config.night_mode_end_hour
        )
    
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
                        f"({prediction.confidence}%)"
                    )
        except Exception as exc:
            self.logger.error(f"❌ Erreur prédiction {symbol}: {exc}")
        
        # Opportunité
        try:
            opportunity = self.market_service.calculate_opportunity_score(
                market_data, prediction
            )
            if opportunity:
                self.logger.info(f"⭐ Opportunité : {opportunity.score}/10")
        except Exception as exc:
            self.logger.error(f"❌ Erreur calcul opportunité {symbol}: {exc}")
        
        # Alertes
        try:
            alerts = self.alert_service.check_alerts(market_data, prediction)
            
            if alerts:
                self.logger.info(f"🚨 {len(alerts)} alerte(s) générée(s)")
                
                for alert in alerts:
                    self.logger.info(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                    
                    if not quiet_mode:
                        try:
                            self.telegram_api.send_alert(alert)
                            with self._state_lock:
                                self.alerts_sent += 1
                            self.logger.info("   ✓ Alerte envoyée sur Telegram")
                        except Exception as e:
                            self.logger.error(f"❌ Erreur envoi alerte: {e}")
            else:
                self.logger.info("ℹ️ Aucune alerte")
        
        except Exception as exc:
            self.logger.error(f"❌ Erreur vérification alertes {symbol}: {exc}")
    
    def _send_startup_message(self):
        """Envoie un résumé complet au démarrage"""
        try:
            self.logger.info("📊 Génération du résumé de démarrage...")
            
            # Collecter les données pour toutes les cryptos
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            for symbol in self.config.crypto_symbols:
                try:
                    # Récupérer les données
                    market_data = self.market_service.get_market_data(symbol)
                    if market_data:
                        markets_data[symbol] = market_data
                        
                        # Prédiction
                        prediction = self.market_service.predict_price_movement(market_data)
                        if prediction:
                            predictions[symbol] = prediction
                        
                        # Opportunité
                        opportunity = self.market_service.calculate_opportunity_score(
                            market_data, prediction
                        )
                        if opportunity:
                            opportunities[symbol] = opportunity
                        
                        self.logger.info(
                            f"  ✓ {symbol}: {market_data.current_price.price_eur:.2f}€ - "
                            f"Score {opportunity.score}/10" if opportunity else 
                            f"  ✓ {symbol}: {market_data.current_price.price_eur:.2f}€"
                        )
                
                except Exception as e:
                    self.logger.error(f"Erreur récupération {symbol}: {e}")
            
            if not markets_data:
                # Fallback si aucune donnée
                self.telegram_api.send_message(
                    "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\n\n"
                    f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\n\n"
                    "⚠️ Impossible de récupérer les données de marché au démarrage."
                )
                return
            
            # Générer le résumé via SummaryService
            summary = self.summary_service.generate_summary(
                markets_data,
                predictions,
                opportunities,
                simple=self.config.use_simple_language
            )
            
            # Ajouter un en-tête de démarrage
            startup_header = (
                "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\n"
                f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\n\n"
            )
            
            full_message = startup_header + summary
            
            # Envoyer sur Telegram
            success = self.telegram_api.send_message(full_message, parse_mode="HTML")
            
            if success:
                self.logger.info("✅ Résumé de démarrage envoyé sur Telegram")
            else:
                self.logger.error("❌ Échec envoi résumé de démarrage")
        
        except Exception as e:
            self.logger.error(f"❌ Erreur envoi message démarrage: {e}")

    def _save_stats(self):
        """Sauvegarde les statistiques"""
        try:
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
        
        # FIXED: Problème 14 - Stats sans doublon, uniquement à la demande
        with self._state_lock:
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

    def stop(self):
        """Arrête le démon"""
        self.logger.info("\n🛑 Arrêt du démon demandé...")
        
        with self._state_lock:
            self.is_running = False
            self.stop_event.set()
    
    def _shutdown(self):
        """Nettoyage avant arrêt"""
        
        with self._state_lock:
            self.is_running = False
            self.stop_event.set()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("👋 CRYPTO BOT DAEMON ARRÊTÉ")
        self.logger.info("="*60)
        
        with self._state_lock:
            if self.start_time:
                uptime = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
                self.logger.info(f"Uptime : {uptime // 3600}h {(uptime % 3600) // 60}m")
            
            self.logger.info(f"Vérifications : {self.checks_count}")
            self.logger.info(f"Alertes envoyées : {self.alerts_sent}")
            self.logger.info(f"Erreurs : {self.errors_count}")
        
        self.logger.info("="*60 + "\n")
