#!/usr/bin/env python3
"""
FIX COMPLET DAEMON - Applique TOUS les fix en une seule fois
1. Import SummaryService
2. Initialisation summary_service
3. Remplace _check_cycle
4. Remplace _send_startup_message
"""

import shutil
from pathlib import Path
from datetime import datetime
import re


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_daemon_complet_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path("daemon/daemon_service.py")
    if src.exists():
        dst = backup_dir / "daemon_service.py"
        shutil.copy2(src, dst)
        print(f"✅ Sauvegarde: {backup_dir}")
    return backup_dir


def apply_all_fixes():
    """Applique tous les fix en une fois"""
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return False
    
    content = file.read_text(encoding='utf-8')
    success_count = 0
    
    # FIX 1: Import SummaryService
    if "from core.services.summary_service import SummaryService" not in content:
        pattern = r"(from core\.services\.notification_generator import NotificationGenerator\n)"
        replacement = r"\1from core.services.summary_service import SummaryService\n"
        content = re.sub(pattern, replacement, content)
        print("✅ Import SummaryService ajouté")
        success_count += 1
    else:
        print("✓  Import SummaryService déjà présent")
    
    # FIX 2: Initialisation summary_service
    if "self.summary_service = SummaryService" not in content:
        pattern = r"(self\.dca_service = DCAService\(\))"
        replacement = r"\1\n        self.summary_service = SummaryService(config)"
        content = re.sub(pattern, replacement, content)
        print("✅ summary_service ajouté dans __init__")
        success_count += 1
    else:
        print("✓  summary_service déjà initialisé")
    
    # FIX 3: Remplacer _check_cycle
    new_check_cycle = '''    def _check_cycle(self):
        """Effectue un cycle avec résumés complets"""
        try:
            current_hour = datetime.now(timezone.utc).hour
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            self.logger.info("\\n" + "="*60)
            self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count + 1}")
            self.logger.info("="*60)
            
            # Récupérer données
            for symbol in self.config.crypto_symbols:
                try:
                    self.logger.info(f"\\n📊 {symbol}:")
                    self.logger.info("-"*60)
                    
                    market_data = self.market_service.get_market_data(symbol)
                    if market_data:
                        markets_data[symbol] = market_data
                        
                        prediction = self.market_service.predict_price_movement(market_data)
                        if prediction:
                            predictions[symbol] = prediction
                            self.logger.info(f"🔮 Prédiction: {prediction.prediction_type.value} ({prediction.confidence:.0f}%)")
                        
                        opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                        if opportunity:
                            opportunities[symbol] = opportunity
                            self.logger.info(f"⭐ Opportunité: {opportunity.score}/10")
                        
                        self.db_service.save_market_data(market_data)
                        if prediction:
                            self.db_service.save_prediction(symbol, prediction)
                except Exception as e:
                    self.logger.error(f"Erreur {symbol}: {e}")
                    self.consecutive_errors += 1
            
            self.checks_count += 1
            
            # Envoyer résumé si heure programmée
            if current_hour in self.config.summary_hours and markets_data:
                if self.last_summary_sent is None or \\\\
                   (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
                    try:
                        self.logger.info(f"\\n⏰ Heure programmée: {current_hour}h")
                        self.logger.info("📤 Envoi du résumé...")
                        
                        summary = self.summary_service.generate_summary(
                            markets_data, predictions, opportunities,
                            simple=self.config.use_simple_language
                        )
                        
                        if summary and self.telegram_api.send_message(summary, parse_mode="HTML"):
                            self.notifications_sent += 1
                            self.last_summary_sent = datetime.now(timezone.utc)
                            self.logger.info("✅ Résumé envoyé")
                        else:
                            self.logger.error("❌ Échec envoi résumé")
                    except Exception as e:
                        self.logger.error(f"Erreur résumé: {e}")
            
            # Alertes
            for symbol, market_data in markets_data.items():
                try:
                    prediction = predictions.get(symbol)
                    alerts = self.alert_service.check_alerts(market_data, prediction)
                    if alerts:
                        self.logger.info(f"\\n🚨 {len(alerts)} alerte(s) pour {symbol}")
                        for alert in alerts:
                            self.telegram_api.send_alert(alert)
                            self.alerts_sent += 1
                except Exception as e:
                    self.logger.error(f"Erreur alertes {symbol}: {e}")
            
            # Stats
            if self.start_time:
                uptime = datetime.now(timezone.utc) - self.start_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                self.logger.info(
                    f"\\n📊 Stats: {self.checks_count} checks, {self.alerts_sent} alertes, "
                    f"{self.notifications_sent} notifs, {self.errors_count} erreurs, "
                    f"Uptime: {hours}h{minutes}m"
                )
            
            if markets_data:
                self.consecutive_errors = 0
        
        except Exception as e:
            self.logger.error(f"Erreur cycle: {e}", exc_info=True)
            self.errors_count += 1
            self.consecutive_errors += 1
'''
    
    pattern = r'    def _check_cycle\(self\):.*?(?=\n    def |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_check_cycle + content[match.end():]
        print("✅ Méthode _check_cycle remplacée")
        success_count += 1
    else:
        print("⚠️ _check_cycle non trouvé")
    
    # FIX 4: Remplacer _send_startup_message
    new_startup = '''    def _send_startup_message(self):
        """Envoie un résumé complet au démarrage"""
        try:
            self.logger.info("📊 Génération du résumé de démarrage...")
            
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
                        opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                        if opportunity:
                            opportunities[symbol] = opportunity
                        self.logger.info(f"  ✓ {symbol}: {market_data.current_price.price_eur:.2f}€")
                except Exception as e:
                    self.logger.error(f"Erreur {symbol}: {e}")
            
            if markets_data:
                summary = self.summary_service.generate_summary(
                    markets_data, predictions, opportunities,
                    simple=self.config.use_simple_language
                )
                startup_header = (
                    "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\\n"
                    f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\\n\\n"
                )
                if self.telegram_api.send_message(startup_header + summary, parse_mode="HTML"):
                    self.logger.info("✅ Résumé de démarrage envoyé")
            else:
                self.telegram_api.send_message("🚀 CRYPTO BOT DÉMARRÉ\\n⚠️ Aucune donnée disponible")
        except Exception as e:
            self.logger.error(f"Erreur démarrage: {e}")
'''
    
    pattern = r'    def _send_startup_message\(self\):.*?(?=\n    def |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_startup + content[match.end():]
        print("✅ Méthode _send_startup_message remplacée")
        success_count += 1
    else:
        print("⚠️ _send_startup_message non trouvé")
    
    # Sauvegarder
    file.write_text(content, encoding='utf-8')
    
    return success_count >= 4


def main():
    print("=" * 60)
    print("🚀 FIX COMPLET DAEMON - TOUT EN UNE FOIS")
    print("=" * 60)
    print()
    
    backup()
    print()
    
    print("📝 Application de TOUS les fix...")
    print()
    
    if apply_all_fixes():
        print()
        print("=" * 60)
        print("✅ TOUS LES FIX APPLIQUÉS AVEC SUCCÈS")
        print("=" * 60)
        print()
        print("🎯 Résultats attendus:")
        print()
        print("  AU DÉMARRAGE:")
        print("    📊 Résumé complet avec analyses")
        print("    💰 Prix, prédictions, opportunités")
        print()
        print("  AUX HEURES PROGRAMMÉES (9h, 12h, 18h UTC):")
        print("    📊 Résumé détaillé automatique")
        print("    ⭐ Meilleures opportunités")
        print()
        print("  EN CONTINU:")
        print("    🚨 Alertes si RSI, Fear&Greed, etc.")
        print()
        print("🧪 Teste maintenant:")
        print("  1. python main.py")
        print("  2. ▶️ Démarrer daemon")
        print("  3. Check Telegram immédiatement → résumé complet")
        print("  4. Attends une heure programmée → autre résumé")
        print()
        return 0
    else:
        print()
        print("=" * 60)
        print("⚠️ CERTAINS FIX N'ONT PAS PU ÊTRE APPLIQUÉS")
        print("=" * 60)
        print()
        print("💡 Lance le diagnostic:")
        print("   python DIAGNOSTIC_DAEMON.py")
        print()
        return 1


if __name__ == "__main__":
    exit(main())
