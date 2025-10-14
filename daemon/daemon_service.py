"""
Daemon Service - Exécution en arrière-plan
"""

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
        self.start_time = datetime.now(timezone.utc)
        
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
                bot_info = self.telegram_api.get_bot_info()
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
        initial_data = {}
        
        # Frais Revolut standards (1.5% par défaut)
        REVOLUT_FEES_PERCENT = 1.5
        INVESTMENT_AMOUNT = 100.0
        
        for symbol in self.config.crypto_symbols:
            try:
                market_data = self.market_service.get_market_data(symbol)
                if market_data:
                    prediction = self.market_service.predict_price_movement(market_data)
                    opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                    
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
                    
                    initial_data[symbol] = {
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
        
        return initial_data
    
    def _send_startup_message(self, initial_data: dict):
        """Envoie un message de démarrage simple et clair"""
        try:
            message = "🚀 <b>BOT CRYPTO - DÉMARRÉ</b>\n\n"
            message += f"📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n\n"
            
            # Analyse simple pour chaque crypto
            if initial_data:
                message += f"━━━━━━━━━━━━━━━━━━━━━\n"
                message += f"💰 <b>ÉTAT DU MARCHÉ</b>\n"
                message += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                for symbol, data in initial_data.items():
                    # En-tête avec recommandation
                    message += f"{data['action_emoji']} <b>{symbol} - {data['action']}</b>\n"
                    message += f"<i>{data['explication']}</i>\n\n"
                    
                    # Prix Revolut
                    message += f"💳 <b>Prix sur Revolut :</b>\n"
                    message += f"   Achat : {data['price_achat']:.2f} €\n"
                    message += f"   Vente : {data['price_vente']:.2f} €\n\n"
                    
                    # Pour 100€
                    message += f"💶 <b>Si j'investis 100€ :</b>\n"
                    message += f"   Frais : {data['frais_100e']:.2f} €\n"
                    message += f"   J'obtiens : {data['quantite_100e']:.6f} {symbol}\n\n"
                    
                    # Tendance
                    message += f"📊 {data['tendance']}\n"
                    message += f"   Évolution 24h : {data['change_24h']:+.1f}%\n"
                    message += f"   Confiance : {data['confidence']}%\n\n"
                    
                    # Sentiment du marché
                    if data.get('fear_greed'):
                        fgi = data['fear_greed']
                        if fgi < 25:
                            sentiment = "😱 Peur extrême"
                            conseil = "(Les gens ont peur, c'est souvent le moment d'acheter)"
                        elif fgi < 45:
                            sentiment = "😨 Peur"
                            conseil = "(Bonne opportunité d'achat)"
                        elif fgi < 55:
                            sentiment = "😐 Neutre"
                            conseil = "(Pas de signal fort)"
                        elif fgi < 75:
                            sentiment = "😊 Optimisme"
                            conseil = "(Marché positif)"
                        else:
                            sentiment = "🤑 Euphorie"
                            conseil = "(Attention, peut-être trop cher)"
                        message += f"   Sentiment : {sentiment}\n"
                        message += f"   {conseil}\n\n"
                    
                    # Pourquoi cette recommandation
                    if data.get('reasons'):
                        message += f"<b>Pourquoi ?</b>\n"
                        for reason in data['reasons']:
                            # Simplifier les raisons techniques
                            reason_simple = reason.replace("RSI", "indicateur technique")
                            reason_simple = reason_simple.replace("survendu", "prix très bas")
                            reason_simple = reason_simple.replace("suracheté", "prix très haut")
                            message += f"   • {reason_simple}\n"
                    
                    message += f"\n{'─'*25}\n\n"
            
            # Configuration
            message += f"━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"⚙️ <b>CONFIGURATION</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"⏱ Vérification toutes les {self.config.check_interval_seconds // 60} minutes\n"
            
            if self.config.enable_alerts:
                message += f"🔔 Alertes activées :\n"
                message += f"   • Si baisse de {self.config.price_drop_threshold}% → je t'alerte\n"
                message += f"   • Si hausse de {self.config.price_spike_threshold}% → je t'alerte\n\n"
            
            # Niveaux configurés en langage simple
            if self.config.enable_price_levels and self.config.price_levels:
                message += f"📊 <b>Niveaux de prix surveillés :</b>\n"
                for symbol, levels in self.config.price_levels.items():
                    if symbol in self.config.crypto_symbols:
                        message += f"   <b>{symbol} :</b>\n"
                        if "low" in levels:
                            message += f"      🟢 Si passe sous {levels['low']:.0f}€ → alerte\n"
                        if "high" in levels:
                            message += f"      🔴 Si passe au-dessus de {levels['high']:.0f}€ → alerte\n"
                message += "\n"
            
            # Mode nuit
            if self.config.enable_quiet_hours:
                message += f"🌙 Mode nuit actif de {self.config.quiet_start_hour}h à {self.config.quiet_end_hour}h\n"
                message += f"   (Alertes importantes uniquement)\n\n"
            
            # Prochainement
            message += f"━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"🚧 <b>BIENTÔT DISPONIBLE</b>\n"
            message += f"━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"• 📊 Graphiques visuels des prix\n"
            message += f"• 💡 Suggestions d'achat progressif (DCA)\n"
            message += f"• 🎯 Calcul automatique de gain/perte\n"
            message += f"• 📱 Dashboard web interactif\n\n"
            
            message += f"✅ <b>Bot en surveillance</b>\n"
            message += f"Je te tiendrai informé des opportunités !\n"
            
            self.telegram_api.send_message(message)
            self.logger.info("✓ Message de démarrage envoyé sur Telegram")
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
        if self.start_time:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
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
        
        uptime = 0
        if self.start_time:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            self.logger.info(f"Uptime : {int(uptime/3600)}h {int((uptime%3600)/60)}m")
        
        self.logger.info(f"Vérifications : {self.checks_count}")
        self.logger.info(f"Alertes envoyées : {self.alerts_sent}")
        self.logger.info(f"Erreurs : {self.errors_count}")
        self.logger.info("="*60 + "\n")
        
        # Message Telegram
        try:
            uptime_str = f"{int(uptime/3600)}h{int((uptime%3600)/60)}m" if self.start_time else "N/A"
            message = "🛑 <b>Crypto Bot Arrêté</b>\n\n"
            message += f"📊 <b>Statistiques:</b>\n"
            message += f"  • Vérifications : {self.checks_count}\n"
            message += f"  • Alertes envoyées : {self.alerts_sent}\n"
            message += f"  • Erreurs : {self.errors_count}\n"
            message += f"  • Uptime : {uptime_str}\n\n"
            message += f"👋 À bientôt !"
            
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
