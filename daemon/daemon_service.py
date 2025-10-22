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
from core.services.broker_service import BrokerService
from core.services.summary_service import SummaryService
from core.models.notification_config import (
    GlobalNotificationSettings,
    CoinNotificationProfile,
    ScheduledNotificationConfig,
    PriceBlock,
    PredictionBlock,
    OpportunityBlock,
    ChartBlock,
    BrokersBlock,
    FearGreedBlock,
    GainLossBlock,
    InvestmentSuggestionBlock,
    GlossaryBlock,
    CustomMessageBlock,
)
from utils.formatters import SafeHTMLFormatter


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
        self.summary_service = SummaryService(config)
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
        FIXED: Problème 8 - Méthode complétée
        Convertit un dictionnaire YAML en GlobalNotificationSettings complet
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

        def _normalize_days(value):
            days: List[int] = []
            if isinstance(value, (int, float)):
                days.append(int(value))
            elif isinstance(value, str):
                for part in value.replace(";", ",").split(","):
                    part = part.strip()
                    if part.isdigit():
                        days.append(int(part))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (int, float)):
                        days.append(int(item))
                    elif isinstance(item, str) and item.strip().isdigit():
                        days.append(int(item.strip()))
            return sorted({d for d in days if 0 <= d <= 6})

        def _apply_block_settings(block, overrides: Optional[Dict[str, Any]]):
            if not overrides or not isinstance(overrides, dict):
                return block
            for key, value in overrides.items():
                target_attr = key
                if not hasattr(block, target_attr):
                    alias_map = {
                        "min_score": "min_opportunity_score",
                        "max_items": "max_suggestions",
                    }
                    target_attr = alias_map.get(key)
                if not target_attr or not hasattr(block, target_attr):
                    continue
                if isinstance(value, list):
                    value = list(value)
                elif isinstance(value, dict):
                    value = dict(value)
                setattr(block, target_attr, value)
            return block

        def _build_custom_blocks(blocks_data: Optional[List[Dict[str, Any]]]):
            custom_blocks: List[CustomMessageBlock] = []
            if not isinstance(blocks_data, list):
                return custom_blocks
            for block_data in blocks_data:
                if not isinstance(block_data, dict):
                    continue
                custom_block = CustomMessageBlock()
                for key, value in block_data.items():
                    if hasattr(custom_block, key):
                        if isinstance(value, list):
                            value = list(value)
                        elif isinstance(value, dict):
                            value = dict(value)
                        setattr(custom_block, key, value)
                custom_blocks.append(custom_block)
            return custom_blocks

        def _build_notification_config(config_data: Optional[Dict[str, Any]], fallback_hours: List[int]) -> ScheduledNotificationConfig:
            cfg = ScheduledNotificationConfig()
            if not config_data:
                cfg.hours = list(fallback_hours)
                return cfg

            if 'name' in config_data:
                cfg.name = config_data['name']
            if 'description' in config_data:
                cfg.description = config_data['description']

            cfg.enabled = config_data.get('enabled', cfg.enabled)
            cfg.hours = _normalize_hours(config_data.get('hours', cfg.hours)) or list(fallback_hours)
            cfg.days_of_week = _normalize_days(config_data.get('days_of_week', cfg.days_of_week))
            if not cfg.days_of_week:
                cfg.days_of_week = [0, 1, 2, 3, 4, 5, 6]

            if 'blocks_order' in config_data and isinstance(config_data['blocks_order'], list):
                cfg.blocks_order = list(config_data['blocks_order'])
            if 'header_message' in config_data:
                cfg.header_message = config_data['header_message']
            if 'footer_message' in config_data:
                cfg.footer_message = config_data['footer_message']

            cfg.kid_friendly_mode = config_data.get('kid_friendly_mode', cfg.kid_friendly_mode)
            cfg.use_emojis_everywhere = config_data.get('use_emojis_everywhere', cfg.use_emojis_everywhere)
            cfg.explain_everything = config_data.get('explain_everything', cfg.explain_everything)
            cfg.avoid_technical_terms = config_data.get('avoid_technical_terms', cfg.avoid_technical_terms)

            cfg.send_only_if_change_above = config_data.get('send_only_if_change_above', cfg.send_only_if_change_above)
            cfg.send_only_if_opportunity_above = config_data.get('send_only_if_opportunity_above', cfg.send_only_if_opportunity_above)

            cfg.price_block = _apply_block_settings(cfg.price_block, config_data.get('price_block'))
            cfg.prediction_block = _apply_block_settings(cfg.prediction_block, config_data.get('prediction_block'))
            cfg.opportunity_block = _apply_block_settings(cfg.opportunity_block, config_data.get('opportunity_block'))
            cfg.chart_block = _apply_block_settings(cfg.chart_block, config_data.get('chart_block'))
            cfg.brokers_block = _apply_block_settings(cfg.brokers_block, config_data.get('brokers_block'))
            cfg.fear_greed_block = _apply_block_settings(cfg.fear_greed_block, config_data.get('fear_greed_block'))
            cfg.gain_loss_block = _apply_block_settings(cfg.gain_loss_block, config_data.get('gain_loss_block'))
            cfg.investment_suggestions_block = _apply_block_settings(cfg.investment_suggestions_block, config_data.get('investment_suggestions_block'))
            cfg.glossary_block = _apply_block_settings(cfg.glossary_block, config_data.get('glossary_block'))
            cfg.custom_blocks = _build_custom_blocks(config_data.get('custom_blocks'))

            return cfg

        notif_data = data.get('notifications', data or {})

        hours = _normalize_hours(notif_data.get('default_scheduled_hours', [9, 12, 18])) or [9, 12, 18]
        quiet_start = int(notif_data.get('quiet_start', 23) or 0)
        quiet_end = int(notif_data.get('quiet_end', 7) or 0)
        quiet_start = max(0, min(23, quiet_start))
        quiet_end = max(0, min(23, quiet_end))

        settings = GlobalNotificationSettings(
            enabled=notif_data.get('enabled', True),
            kid_friendly_mode=notif_data.get('kid_friendly_mode', True),
            use_emojis_everywhere=notif_data.get('use_emojis_everywhere', True),
            explain_everything=notif_data.get('explain_everything', True),
            respect_quiet_hours=notif_data.get('respect_quiet_hours', True),
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            default_scheduled_hours=hours
        )

        coins_data = data.get('coins', {}) or {}
        if isinstance(coins_data, dict):
            settings.coin_profiles.clear()
            for symbol, coin_cfg in coins_data.items():
                if not isinstance(coin_cfg, dict):
                    continue

                profile = CoinNotificationProfile(
                    symbol=symbol,
                    enabled=coin_cfg.get('enabled', True)
                )
                profile.nickname = coin_cfg.get('nickname') or coin_cfg.get('name') or profile.nickname
                profile.custom_emoji = coin_cfg.get('custom_emoji') or profile.custom_emoji
                profile.intro_message = coin_cfg.get('intro_message') or profile.intro_message
                profile.outro_message = coin_cfg.get('outro_message') or profile.outro_message
                profile.detail_level = coin_cfg.get('detail_level', profile.detail_level)

                scheduled_configs = coin_cfg.get('scheduled_notifications', [])
                profile.scheduled_notifications = []
                if isinstance(scheduled_configs, list) and scheduled_configs:
                    for sched_cfg in scheduled_configs:
                        if not isinstance(sched_cfg, dict):
                            continue
                        notification_config = _build_notification_config(sched_cfg, hours)
                        profile.add_scheduled_notification(notification_config)
                else:
                    for hour in hours:
                        default_config = ScheduledNotificationConfig(
                            name=f"Notification {hour}h",
                            hours=[hour],
                            enabled=profile.enabled
                        )
                        profile.add_scheduled_notification(default_config)

                default_config_data = coin_cfg.get('default_config')
                if isinstance(default_config_data, dict):
                    profile.default_config = _build_notification_config(default_config_data, hours)

                settings.coin_profiles[symbol] = profile

        return settings

    def update_notification_settings(self, settings: GlobalNotificationSettings) -> None:
        """Met à jour les paramètres de notification et régénère le générateur associé."""
        with self._state_lock:
            self.notification_settings = settings
            self.broker_service = BrokerService(self.config)
            self.notification_generator = NotificationGenerator(
                settings, 
                self.config.crypto_symbols,
                broker_service=self.broker_service
            )

    def update_configuration(self, config: BotConfiguration) -> None:
        """Met à jour les services internes avec une nouvelle configuration."""
        with self._state_lock:
            self.config = config
            # Recréer les services si nécessaire
            self.alert_service = AlertService(config)
            self.broker_service = BrokerService(config)
            self.notification_generator = NotificationGenerator(self.notification_settings, config.crypto_symbols, broker_service=self.broker_service)
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
        """Effectue un cycle de vérification - N'ENVOIE QUE LES NOTIFICATIONS CONFIGURÉES"""
        try:
            current_hour = datetime.now(timezone.utc).hour
            current_day = datetime.now(timezone.utc).weekday()
            
            # Vérifier si c'est l'heure d'envoyer un résumé
            should_send_summary = False
            if current_hour in self.config.summary_hours:
                if self.last_summary_sent is None or \
                   (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
                    should_send_summary = True
            
            if not should_send_summary:
                # Pas l'heure programmée, ne rien envoyer
                return
            
            self.logger.info(f"\n⏰ Heure programmée: {current_hour}h - Génération des notifications...")
            
            # Collecter TOUTES les données en une seule fois
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            for symbol in self.config.crypto_symbols:
                try:
                    market = self.market_service.get_market_data(symbol)
                    if market:
                        markets_data[symbol] = market
                        predictions[symbol] = self.market_service.predict_price_movement(market)
                        opportunities[symbol] = self.market_service.calculate_opportunity_score(
                            market, predictions[symbol]
                        )
                except Exception as e:
                    self.logger.error(f"Erreur récupération {symbol}: {e}")
            
            if not markets_data:
                self.logger.warning("Aucune donnée de marché disponible")
                return
            
            with self._state_lock:
                self.checks_count += 1
            
            # ENVOYER UNE NOTIFICATION PAR CRYPTO (selon configuration)
            for symbol in self.config.crypto_symbols:
                if symbol not in markets_data:
                    continue
                
                try:
                    market = markets_data[symbol]
                    prediction = predictions.get(symbol)
                    opportunity = opportunities.get(symbol)
                    
                    # GÉNÉRER LA NOTIFICATION AVEC LE GÉNÉRATEUR
                    # Celui-ci respecte AUTOMATIQUEMENT la config YAML
                    notification_message = self.notification_generator.generate_notification(
                        symbol=symbol,
                        market=market,
                        prediction=prediction,
                        opportunity=opportunity,
                        all_markets=markets_data,
                        all_predictions=predictions,
                        all_opportunities=opportunities,
                        current_hour=current_hour,
                        current_day_of_week=current_day
                    )
                    
                    # ENVOYER SI MESSAGE GÉNÉRÉ
                    if notification_message:
                        success = self.telegram_api.send_message(
                            notification_message,
                            parse_mode="HTML"
                        )
                        
                        if success:
                            with self._state_lock:
                                self.notifications_sent += 1
                            self.logger.info(f"✓ Notification {symbol} envoyée")
                        else:
                            self.logger.error(f"✗ Échec envoi {symbol}")
                    else:
                        self.logger.info(f"⊗ Pas de notification pour {symbol} (heures/seuils)")
                
                except Exception as e:
                    self.logger.error(f"Erreur notification {symbol}: {e}", exc_info=True)
                    with self._state_lock:
                        self.errors_count += 1
            
            # Marquer comme envoyé
            with self._state_lock:
                self.last_summary_sent = datetime.now(timezone.utc)
            
            # Reset erreurs consécutives si succès
            if markets_data:
                with self._state_lock:
                    self.consecutive_errors = 0
        
        except Exception as e:
            self.logger.error(f"❌ Erreur cycle : {e}", exc_info=True)
            with self._state_lock:
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
        """Envoie un message de démarrage selon notifications.yaml (FORCÉ)"""
        try:
            self.logger.info("📊 Génération du message de démarrage...")
            
            # En-tête de démarrage
            startup_header = (
                "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\n"
                f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\n\n"
            )
            
            # Collecter les données
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            for symbol in self.config.crypto_symbols:
                try:
                    market_data = self.market_service.get_market_data(symbol)
                    if market_data:
                        markets_data[symbol] = market_data
                        prediction = self.market_service.predict_price_movement(market_data)
                        if prediction:
                            predictions[symbol] = prediction
                        opportunity = self.market_service.calculate_opportunity_score(
                            market_data, prediction
                        )
                        if opportunity:
                            opportunities[symbol] = opportunity
                        
                        self.logger.info(f"  ✓ {symbol}: {market_data.current_price.price_eur:.2f}€")
                
                except Exception as e:
                    self.logger.error(f"Erreur récupération {symbol}: {e}")
            
            if not markets_data:
                self.telegram_api.send_message(
                    startup_header + "⚠️ Impossible de récupérer les données de marché."
                )
                return
            
            # FORCER NotificationGenerator même si pas l'heure programmée
            all_notifications = []
            current_time = datetime.now(timezone.utc)
            current_hour = current_time.hour
            current_day = current_time.weekday()
            
            for symbol in markets_data.keys():
                try:
                    # Récupérer le profil
                    profile = self.notification_settings.get_coin_profile(symbol)
                    if not profile or not profile.enabled:
                        continue
                    
                    # IMPORTANT: Utiliser la PREMIÈRE config disponible
                    # même si ce n'est pas l'heure programmée
                    config = None
                    if profile.scheduled_notifications:
                        config = profile.scheduled_notifications[0]
                    elif profile.default_config:
                        config = profile.default_config
                    
                    if not config:
                        self.logger.warning(f"Aucune config pour {symbol}")
                        continue
                    
                    # GÉNÉRER LA NOTIFICATION MANUELLEMENT
                    # en utilisant les blocs configurés dans blocks_order
                    message_parts = []
                    
                    # Header personnalisé
                    emoji = profile.custom_emoji or "💎"
                    header = f"🔔 <b>{emoji} {profile.nickname or symbol}</b>"
                    message_parts.append(header)
                    
                    # Générer chaque bloc selon blocks_order
                    # Note: NotificationGenerator et BrokerService déjà importés en haut
                    
                    # Créer un générateur temporaire pour utiliser ses méthodes de blocs
                    temp_gen = NotificationGenerator(
                        self.notification_settings, 
                        self.config.crypto_symbols,
                        broker_service=self.broker_service
                    )
                    
                    for block_name in config.blocks_order:
                        try:
                            block_content = temp_gen._generate_block(
                                block_name=block_name,
                                config=config,
                                symbol=symbol,
                                market=markets_data[symbol],
                                prediction=predictions.get(symbol),
                                opportunity=opportunities.get(symbol),
                                all_markets=markets_data,
                                all_predictions=predictions,
                                all_opportunities=opportunities,
                            )
                            
                            if block_content:
                                message_parts.append(block_content)
                        
                        except Exception as e:
                            self.logger.error(f"Erreur bloc {block_name} pour {symbol}: {e}")
                    
                    # Footer
                    footer = config.footer_message or "ℹ️ Ceci n'est pas un conseil financier"
                    message_parts.append(footer)
                    
                    if message_parts:
                        notification = "\n\n".join(message_parts)
                        all_notifications.append(notification)
                
                except Exception as e:
                    self.logger.error(f"Erreur notification {symbol}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            if not all_notifications:
                self.logger.warning("Aucune notification générée")
                return
            
            # Assembler
            full_message = startup_header + "\n\n".join(all_notifications)
            
            max_len = getattr(self.notification_settings, "max_message_length", 4096)
            max_len = min(max_len, 4000)  # marge pour la mise en forme
            split_limit = max(500, max_len - 16)
            chunks = self._split_html_message(full_message, split_limit)
            formatter = SafeHTMLFormatter()
            
            success = True
            total = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                if total > 1:
                    part_prefix = f"[{idx}/{total}]\n"
                    available_len = max_len - len(part_prefix)
                else:
                    part_prefix = ""
                    available_len = max_len
                
                if len(chunk) > available_len:
                    chunk = formatter.truncate_safely(chunk, available_len)
                
                chunk_to_send = f"{part_prefix}{chunk}"
                
                if not self.telegram_api.send_message(chunk_to_send, parse_mode="HTML"):
                    success = False
                    break
            
            if success:
                self.logger.info("✅ Message de démarrage envoyé (notifications.yaml respecté)")
            else:
                self.logger.error("❌ Échec envoi message de démarrage")
        
        except Exception as e:
            self.logger.error(f"❌ Erreur message démarrage: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def _split_html_message(self, message: str, max_length: int) -> List[str]:
        """Découpe un message HTML en blocs respectant la limite Telegram."""
        if len(message) <= max_length:
            return [message]
        
        sections = message.split("\n\n")
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0
        
        for raw_section in sections:
            section = raw_section.strip("\n")
            if not section:
                continue
            
            addition_len = len(section) if not current else len(section) + 2  # +2 pour le double saut de ligne
            
            if current and current_len + addition_len > max_length:
                chunks.append("\n\n".join(current))
                current = [section]
                current_len = len(section)
            else:
                if current:
                    current.append(section)
                    current_len += addition_len
                else:
                    current = [section]
                    current_len = len(section)
        
        if current:
            chunks.append("\n\n".join(current))
        
        # Vérifier qu'aucun chunk ne dépasse la limite; en cas de dépassement, couper grossièrement
        safe_chunks: List[str] = []
        for chunk in chunks:
            if len(chunk) <= max_length:
                safe_chunks.append(chunk)
            else:
                start = 0
                end = len(chunk)
                while start < end:
                    safe_chunks.append(chunk[start:start + max_length])
                    start += max_length
        
        return safe_chunks or [message[:max_length]]

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
