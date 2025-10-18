"""
Daemon Service - Exécution en arrière-plan
"""

import time
import signal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from threading import Event

from core.models import BotConfiguration, AlertLevel
from api.binance_api import BinanceAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from utils.logger import setup_logger
from core.services.database_service import DatabaseService
from core.services.chart_service import ChartService
from api.enhanced_telegram_api import EnhancedTelegramAPI
from core.services.summary_service import SummaryService
from core.services.report_service import ReportService
from core.services.dca_service import DCAService


class DaemonService:
    def __init__(self, config: BotConfiguration):
        self.config = config

        # État d'exécution
        self.is_running = False
        self.stop_event = Event()
        self.start_time: Optional[datetime] = None
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0

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
        self.summary_service = SummaryService(config)
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
        self.summary_service = SummaryService(config)
        self.report_service.configure(config)
        self.telegram_api.message_delay = config.telegram_message_delay

    # ------------------------------------------------------------------
    # Helpers per-coin
    # ------------------------------------------------------------------
    def _coin_option(self, symbol: str, key: str, default):
        settings = getattr(self.config, "coin_settings", {}) or {}
        return settings.get(symbol, {}).get(key, default)

    def _coin_send_chart(self, symbol: str) -> bool:
        return bool(self._coin_option(symbol, "send_chart", self.config.send_summary_chart))

    def _coin_send_dca(self, symbol: str) -> bool:
        return bool(self._coin_option(symbol, "send_dca", self.config.send_summary_dca))

    def _coin_investment_amount(self, symbol: str) -> float:
        return float(self._coin_option(symbol, "investment_amount", self.config.investment_amount))

    def _check_cycle(self):
        """Exécute un cycle de vérification complet avec gestion du mode nuit."""
        
        quiet_mode = False
        if self.config.enable_quiet_hours and self._is_quiet_hours():
            quiet_mode = True
            self.logger.info("Mode nuit actif - vérification silencieuse")
        
        self.checks_count += 1
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count}")
        self.logger.info(f"{'='*60}")
        
        for symbol in self.config.crypto_symbols:
            try:
                self._process_symbol(symbol, quiet_mode)
            except Exception as exc:
                self.logger.error(f"Erreur lors de la vérification de {symbol}: {exc}", exc_info=True)
                self.errors_count += 1
        
        if not quiet_mode and self.summary_service.should_send_summary():
            self._send_auto_summary()
        
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
        
        self.db_service.save_stats(
            self.checks_count,
            self.alerts_sent,
            self.errors_count,
            uptime_seconds
        )
        
        if self.start_time:
            self.logger.info(
                f"\n📊 Stats : {self.checks_count} vérifications, "
                f"{self.alerts_sent} alertes, {self.errors_count} erreurs, "
                f"Uptime: {uptime_seconds // 3600}h{(uptime_seconds % 3600) // 60}m"
            )
        
        if self.checks_count % 100 == 0:
            self.db_service.cleanup_old_data(self.config.keep_history_days)

    def _process_symbol(self, symbol: str, quiet_mode: bool) -> None:
        """Analyse et traite une crypto pour un cycle donné."""
        self.logger.info(f"\n📊 {symbol}:")
        self.logger.info("-" * 60)
        
        market_data = self.market_service.get_market_data(symbol)
        if not market_data or not market_data.current_price:
            self.logger.warning(f"Impossible de récupérer les données pour {symbol}")
            return
        
        # Sauvegarder le prix courant
        try:
            self.db_service.save_price(market_data.current_price)
        except Exception as exc:
            self.logger.error(f"Erreur sauvegarde prix {symbol}: {exc}", exc_info=True)
        
        price = market_data.current_price.price_eur
        change_24h = market_data.current_price.change_24h
        
        price_display = f"{price:.2f} €" if price is not None else "indisponible"
        change_display = f"{change_24h:+.2f}%" if change_24h is not None else "indisponible"
        self.logger.info(f"💰 Prix : {price_display} ({change_display} 24h)")
        
        prediction = self.market_service.predict_price_movement(market_data)
        self.logger.info(
            f"🔮 Prédiction : {prediction.prediction_type.value} ({prediction.confidence}%)"
        )
        
        opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
        self.logger.info(f"⭐ Opportunité : {opportunity.score}/10")
        
        alerts = self.alert_service.check_alerts(market_data, prediction)
        if not alerts:
            self.logger.info("ℹ️ Aucune alerte")
            return
        
        self.logger.info(f"🚨 {len(alerts)} alerte(s) générée(s)")
        
        for alert in alerts:
            self.logger.info(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
            
            try:
                self.db_service.save_alert(alert)
            except Exception as exc:
                self.logger.error(f"   ✗ Erreur sauvegarde alerte : {exc}", exc_info=True)
            
            should_send = alert.alert_level in (AlertLevel.IMPORTANT, AlertLevel.CRITICAL)
            if quiet_mode:
                should_send = (
                    self.config.quiet_allow_critical and alert.alert_level == AlertLevel.CRITICAL
                )
            
            if not should_send:
                continue
            
            try:
                sent = self.telegram_api.send_alert(alert, include_metadata=True)
                if sent:
                    self.alerts_sent += 1
                    self.logger.info("   ✓ Alerte envoyée sur Telegram")
                else:
                    self.logger.warning("   ✗ Échec envoi Telegram")
            except Exception as exc:
                self.logger.error(f"   ✗ Erreur envoi Telegram : {exc}", exc_info=True)
    
    def _is_quiet_hours(self) -> bool:
        """Vérifie si on est en heures silencieuses"""
        current_hour = datetime.now().hour
        start = self.config.quiet_start_hour
        end = self.config.quiet_end_hour
        
        if start < end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end
    
    def _send_auto_summary(self):
        """Envoie un résumé automatique"""
        try:
            markets_data: Dict[str, Any] = {}
            predictions: Dict[str, Any] = {}
            opportunities: Dict[str, Any] = {}

            for symbol in self.config.crypto_symbols:
                market = self.market_service.get_market_data(symbol)
                if market:
                    markets_data[symbol] = market
                    predictions[symbol] = self.market_service.predict_price_movement(market)
                    opportunities[symbol] = self.market_service.calculate_opportunity_score(
                        market, predictions[symbol]
                    )

            if not self.config.notification_per_coin:
                summary = self.summary_service.generate_summary(
                    markets_data,
                    predictions,
                    opportunities,
                    simple=self.config.use_simple_language,
                )
                self.telegram_api.send_message(summary, use_queue=False)

                if self.config.enable_graphs:
                    chart = self.chart_service.generate_comparison_chart(markets_data)
                    if chart:
                        self.telegram_api.send_photo(chart, "Comparaison des cryptos")

            self._send_summary_extras(markets_data, predictions, opportunities)

        except Exception as e:
            self.logger.error(f"Erreur résumé automatique: {e}")

    def _send_summary_extras(self, markets_data: Dict[str, Any],
                              predictions: Dict[str, Any],
                              opportunities: Dict[str, Any]) -> None:
        if not markets_data:
            return
        symbols = sorted(
            symbol for symbol in markets_data.keys()
            if not self.config.coin_settings
            or self.config.coin_settings.get(symbol.upper(), {}).get("include_summary", True)
        )
        if not symbols:
            return

        for symbol in symbols:
            market = markets_data.get(symbol)
            prediction = predictions.get(symbol)
            opportunity = opportunities.get(symbol)

            notification = self.report_service.generate_coin_notification(symbol, market, prediction, opportunity)
            if notification:
                try:
                    self.telegram_api.send_message(notification, use_queue=False)
                except Exception as exc:
                    self.logger.error(f"Erreur notification {symbol}: {exc}")

            notif_opts = self.report_service.get_notification_options(symbol)
            show_curves = notif_opts.get(
                "show_curves",
                self.config.notification_include_chart,
            )
            if not show_curves:
                continue

            timeframes = self.report_service.get_notification_timeframes(symbol)
            for timeframe in timeframes:
                try:
                    history = self.market_service.get_price_history(symbol, hours=timeframe)
                    if not history:
                        continue
                    price_levels = None
                    if self.config.enable_price_levels and self.config.price_levels:
                        price_levels = self.config.price_levels.get(symbol)
                    chart = self.chart_service.generate_price_chart(
                        symbol,
                        history,
                        show_levels=self.config.show_levels_on_graph,
                        price_levels=price_levels,
                    )
                    if chart:
                        caption = f"{symbol} — Graphique {timeframe}h"
                        try:
                            self.telegram_api.send_photo(chart, caption, use_queue=False)
                        finally:
                            chart.close()
                except Exception as exc:
                    self.logger.error(f"Erreur graphique {symbol} ({timeframe}h): {exc}")

        if self.config.notification_send_glossary:
            glossary_text = self.report_service.generate_glossary_notification()
            if glossary_text:
                try:
                    self.telegram_api.send_message(glossary_text, use_queue=False)
                except Exception as exc:
                    self.logger.error(f"Erreur notification glossaire: {exc}")
        if self.config.notification_per_coin:
            return

        best_symbol = None
        if opportunities:
            best_symbol = max(opportunities.items(), key=lambda item: item[1].score)[0]
        if not best_symbol:
            best_symbol = next(iter(markets_data.keys()), None)
        if not best_symbol:
            return

        if self._coin_send_chart(best_symbol):
            try:
                history = self.market_service.get_price_history(best_symbol, hours=24)
                if history:
                    price_levels = None
                    if self.config.enable_price_levels and self.config.price_levels:
                        price_levels = self.config.price_levels.get(best_symbol)
                    chart = self.chart_service.generate_price_chart(
                        best_symbol,
                        history,
                        show_levels=self.config.show_levels_on_graph,
                        price_levels=price_levels,
                    )
                    if chart:
                        caption = f"Graphique 24h de {best_symbol}"
                        try:
                            self.telegram_api.send_photo(chart, caption, use_queue=False)
                        finally:
                            chart.close()
            except Exception as exc:
                self.logger.error(f"Erreur envoi graphique {best_symbol}: {exc}")

        if self._coin_send_dca(best_symbol):
            market = markets_data.get(best_symbol)
            prediction = predictions.get(best_symbol)
            opportunity = opportunities.get(best_symbol)
            if market and prediction and opportunity and getattr(market, "current_price", None):
                try:
                    plan = self.dca_service.generate_dca_plan(
                        best_symbol,
                        self._coin_investment_amount(best_symbol),
                        market.current_price.price_eur,
                        market,
                        prediction,
                        opportunity,
                    )
                    message = self.dca_service.format_dca_message(
                        plan,
                        simple=self.config.use_simple_language,
                    )
                    self.telegram_api.send_message(message, use_queue=False)
                except Exception as exc:
                    self.logger.error(f"Erreur envoi DCA {best_symbol}: {exc}")

    def _signal_handler(self, signum, frame):
        """Handler pour signaux système"""
        self.logger.info(f"Signal {signum} reçu, arrêt du démon...")
        self.stop()
    
    def start(self):
        """Démarre le service démon"""
        if self.is_running:
            self.logger.warning("Le démon est déjà en cours d'exécution")
            return

        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            self.logger.error("❌ Configuration Telegram invalide pour le démon")
            return

        self.stop_event.clear()
        
        self.is_running = True
        self.checks_count = 0
        self.alerts_sent = 0
        self.errors_count = 0
        self.start_time = datetime.now(timezone.utc)

        # Démarrer la queue Telegram avant les premiers envois
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
            self.logger.error("❌ Connexion Telegram échouée ! Vérifiez votre configuration.")
            try:
                self.telegram_api.stop_queue()
            except Exception:
                pass
            self.is_running = False
            return
        
        # Récupérer état initial du marché
        initial_data = self._get_initial_market_state()
        
        # Envoyer message de démarrage
        if self.config.enable_startup_summary:
            self._send_startup_message(initial_data)

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
            self.logger.info("🔍 Test de connexion Telegram...")
            success = self.telegram_api.test_connection()
            if success:
                bot_info = None
                if hasattr(self.telegram_api, "get_bot_info"):
                    try:
                        bot_info = self.telegram_api.get_bot_info()
                    except Exception as info_error:
                        self.logger.debug(f"Impossible de récupérer les infos du bot: {info_error}")
                if bot_info:
                    self.logger.info(f"✓ Connecté au bot: @{bot_info.get('username', 'unknown')}")
                else:
                    self.logger.info("✓ Connexion Telegram OK")
            return success
        except Exception as e:
            self.logger.error(f"Erreur test Telegram : {e}")
            return False
    
    def _get_initial_market_state(self) -> dict:
        """Récupère l'état initial du marché"""
        self.logger.info("📊 Récupération état initial du marché...")
        summary_data: Dict[str, Dict[str, Any]] = {}
        markets_data: Dict[str, Any] = {}
        predictions_data: Dict[str, Any] = {}
        opportunities_data: Dict[str, Any] = {}
        
        # Frais Revolut standards (1.5% par défaut)
        REVOLUT_FEES_PERCENT = 1.5
        INVESTMENT_AMOUNT = 100.0
        
        for symbol in self.config.crypto_symbols:
            try:
                market_data = self.market_service.get_market_data(symbol)
                if market_data:
                    markets_data[symbol] = market_data
                    prediction = self.market_service.predict_price_movement(market_data)
                    predictions_data[symbol] = prediction
                    opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                    opportunities_data[symbol] = opportunity
                    
                    # Prix Revolut (avec spread estimé)
                    price_market = market_data.current_price.price_eur
                    spread = 0.005  # 0.5% de spread
                    price_achat = price_market * (1 + spread)  # Prix pour acheter
                    price_vente = price_market * (1 - spread)  # Prix pour vendre
                    
                    # Calcul pour 100€
                    frais = INVESTMENT_AMOUNT * (REVOLUT_FEES_PERCENT / 100)
                    montant_investi = INVESTMENT_AMOUNT - frais
                    quantite = montant_investi / price_achat
                    
                    # Recommandation simple
                    if opportunity.score >= 8:
                        action = "ACHETER MAINTENANT"
                        action_emoji = "🟢"
                        explication = "Excellent moment pour investir"
                    elif opportunity.score >= 7:
                        action = "BON MOMENT"
                        action_emoji = "🟢"
                        explication = "Bonne opportunité d'achat"
                    elif opportunity.score >= 5:
                        action = "ATTENDRE UN PEU"
                        action_emoji = "🟡"
                        explication = "Moment neutre, pas urgent"
                    else:
                        action = "NE PAS ACHETER"
                        action_emoji = "🔴"
                        explication = "Attendre une meilleure occasion"
                    
                    # Tendance simple
                    if prediction.prediction_type.value in ["HAUSSIER", "LÉGÈREMENT HAUSSIER"]:
                        tendance = "Va probablement monter 📈"
                    elif prediction.prediction_type.value in ["BAISSIER", "LÉGÈREMENT BAISSIER"]:
                        tendance = "Va probablement baisser 📉"
                    else:
                        tendance = "Stable ➡️"
                    
                    summary_data[symbol] = {
                        'price_achat': price_achat,
                        'price_vente': price_vente,
                        'change_24h': market_data.current_price.change_24h,
                        'frais_100e': frais,
                        'quantite_100e': quantite,
                        'action': action,
                        'action_emoji': action_emoji,
                        'explication': explication,
                        'tendance': tendance,
                        'confidence': prediction.confidence,
                        'opportunity': opportunity.score,
                        'reasons': opportunity.reasons[:2],
                        'fear_greed': market_data.fear_greed_index
                    }
                    
                    self.logger.info(f"  • {symbol}: {price_achat:.2f}€ - {action}")
            except Exception as e:
                self.logger.error(f"  ✗ Erreur {symbol}: {e}")
        
        return {
            "summary": summary_data,
            "markets": markets_data,
            "predictions": predictions_data,
            "opportunities": opportunities_data,
        }
    
    def _send_startup_message(self, initial_data: dict):
        """Envoie un message de démarrage et les notifications par crypto"""
        try:
            summary_data: Dict[str, Dict[str, Any]] = initial_data.get("summary", {}) if isinstance(initial_data, dict) else {}
            markets = initial_data.get("markets", {}) if isinstance(initial_data, dict) else {}
            predictions = initial_data.get("predictions", {}) if isinstance(initial_data, dict) else {}
            opportunities = initial_data.get("opportunities", {}) if isinstance(initial_data, dict) else {}

            header_lines: List[str] = [
                "🚀 <b>BOT CRYPTO - DÉMARRÉ</b>",
                "",
                f"📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                f"📍 Cryptos surveillées : {', '.join(self.config.crypto_symbols)}",
                f"⏱ Vérification toutes les {self.config.check_interval_seconds // 60} minutes",
            ]

            if self.config.enable_alerts:
                header_lines.append(
                    f"🔔 Alertes prix actives (−{self.config.price_drop_threshold}% / +{self.config.price_spike_threshold}%)"
                )
            if self.config.notification_per_coin:
                header_lines.append("💬 Notifications individuelles activées pour chaque crypto")
            if self.config.enable_quiet_hours:
                header_lines.append(
                    f"🌙 Mode nuit : {self.config.quiet_start_hour}h → {self.config.quiet_end_hour}h "
                    "(impose silence sauf urgence)"
                )

            self.telegram_api.send_message("\n".join(header_lines), use_queue=False)
            self.logger.info("✓ Message de démarrage envoyé sur Telegram")

            sent_any = False
            for symbol in self.config.crypto_symbols:
                notification = self.report_service.generate_coin_notification(
                    symbol,
                    markets.get(symbol),
                    predictions.get(symbol),
                    opportunities.get(symbol),
                )
                if notification:
                    try:
                        self.telegram_api.send_message(notification, use_queue=False)
                        sent_any = True
                        continue
                    except Exception as exc:
                        self.logger.error(f"Erreur notification démarrage {symbol}: {exc}")

                summary_entry = summary_data.get(symbol)
                if summary_entry:
                    fallback_msg = self._build_coin_summary_message(symbol, summary_entry)
                    if fallback_msg:
                        try:
                            self.telegram_api.send_message(fallback_msg, use_queue=False)
                            sent_any = True
                        except Exception as exc:
                            self.logger.error(f"Erreur fallback démarrage {symbol}: {exc}")
                else:
                    self.logger.warning(f"Aucune donnée disponible pour {symbol} au démarrage.")

            if not sent_any and summary_data:
                fallback = self._build_startup_summary_block(summary_data)
                if fallback:
                    self.telegram_api.send_message(fallback, use_queue=False)
                    self.logger.info("Message de démarrage fallback (résumé) envoyé")
            if not sent_any:
                missing_symbols = [
                    symbol for symbol in self.config.crypto_symbols
                    if symbol not in summary_data and symbol not in markets
                ]
                for symbol in missing_symbols:
                    try:
                        self.telegram_api.send_message(
                            f"ℹ️ {symbol} — données indisponibles pour le moment, je retente au prochain cycle.",
                            use_queue=False,
                        )
                    except Exception as exc:
                        self.logger.error(f"Erreur notification indisponibilité {symbol}: {exc}")
        except Exception as e:
            self.logger.error(f"Erreur envoi message démarrage : {e}")

    @staticmethod
    def _build_coin_summary_message(symbol: str, data: Dict[str, Any]) -> str:
        if not data:
            return ""

        action = data.get("action", "SURVEILLER")
        emoji = data.get("action_emoji", "ℹ️")
        explanation = data.get("explication", "")
        price_buy = data.get("price_achat")
        price_sell = data.get("price_vente")
        change_24h = data.get("change_24h")
        tendance = data.get("tendance")
        fear_greed = data.get("fear_greed")
        reasons = data.get("reasons") or []

        lines: List[str] = [f"{emoji} <b>{symbol} — {action}</b>"]
        if explanation:
            lines.append(explanation)

        if price_buy is not None and price_sell is not None:
            lines.append(f"Prix estimé : achat {price_buy:.2f}€ | vente {price_sell:.2f}€")

        if change_24h is not None:
            lines.append(f"Variation 24h : {change_24h:+.1f}%")

        if tendance:
            lines.append(tendance)

        if fear_greed is not None:
            lines.append(f"Sentiment (FGI) : {fear_greed}/100")

        cleaned_reasons: List[str] = []
        for reason in reasons:
            reason_simple = str(reason)
            reason_simple = reason_simple.replace("RSI", "indicateur de force")
            reason_simple = reason_simple.replace("survendu", "niveau très bas")
            reason_simple = reason_simple.replace("suracheté", "niveau très haut")
            cleaned_reasons.append(reason_simple)

        if cleaned_reasons:
            lines.append("Pourquoi :")
            for item in cleaned_reasons:
                lines.append(f"• {item}")

        return "\n".join(lines).strip()

    @staticmethod
    def _build_startup_summary_block(summary_data: Dict[str, Dict[str, Any]]) -> str:
        if not summary_data:
            return ""

        sections: List[str] = []
        for symbol, data in summary_data.items():
            section = DaemonService._build_coin_summary_message(symbol, data)
            if section:
                sections.append(section)

        if not sections:
            return ""

        return "💡 Synthèse rapide\n\n" + "\n\n".join(sections)
    
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
        
        try:
            self.telegram_api.stop_queue()
        except Exception:
            pass

        # Message Telegram
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
