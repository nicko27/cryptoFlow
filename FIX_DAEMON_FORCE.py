#!/usr/bin/env python3
"""
FIX DAEMON - Version automatique forcée
Remplace directement la méthode _check_cycle
"""

import shutil
from pathlib import Path
from datetime import datetime
import re


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_daemon_force_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path("daemon/daemon_service.py")
    if src.exists():
        dst = backup_dir / "daemon_service.py"
        shutil.copy2(src, dst)
        print(f"✅ Sauvegarde: {backup_dir}")
    return backup_dir


def fix_imports(content):
    """Ajoute les imports nécessaires"""
    
    if "from core.services.summary_service import SummaryService" not in content:
        # Trouver la ligne après NotificationGenerator
        pattern = r"(from core\.services\.notification_generator import NotificationGenerator\n)"
        replacement = r"\1from core.services.summary_service import SummaryService\n"
        content = re.sub(pattern, replacement, content)
        print("✅ Import SummaryService ajouté")
    
    return content


def fix_init(content):
    """Ajoute summary_service dans __init__"""
    
    if "self.summary_service = SummaryService" not in content:
        # Trouver après dca_service
        pattern = r"(self\.dca_service = DCAService\(\))"
        replacement = r"\1\n        self.summary_service = SummaryService(config)"
        content = re.sub(pattern, replacement, content)
        print("✅ summary_service ajouté dans __init__")
    
    return content


def fix_check_cycle(content):
    """Remplace complètement _check_cycle"""
    
    # Nouvelle implémentation
    new_check_cycle = '''    def _check_cycle(self):
        """Effectue un cycle de vérification avec résumés complets"""
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
                if self.last_summary_sent is None or \\\\
                   (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
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
'''
    
    # Trouver _check_cycle avec regex robuste
    # Cherche de "def _check_cycle" jusqu'à la prochaine "def " au même niveau d'indentation
    pattern = r'    def _check_cycle\(self\):.*?(?=\n    def |\n\nclass |\Z)'
    
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        content = content[:match.start()] + new_check_cycle + content[match.end():]
        print("✅ Méthode _check_cycle remplacée")
        return content, True
    else:
        print("⚠️ _check_cycle non trouvé")
        return content, False


def main():
    print("=" * 60)
    print("🔧 FIX DAEMON - Version forcée automatique")
    print("=" * 60)
    print()
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return 1
    
    backup()
    print()
    
    print("📝 Application des corrections...")
    content = file.read_text(encoding='utf-8')
    
    # Appliquer les fixes
    content = fix_imports(content)
    content = fix_init(content)
    content, success = fix_check_cycle(content)
    
    if success:
        # Sauvegarder
        file.write_text(content, encoding='utf-8')
        
        print()
        print("=" * 60)
        print("✅ FIX APPLIQUÉ AVEC SUCCÈS")
        print("=" * 60)
        print()
        print("🧪 Teste maintenant:")
        print("  1. python main.py")
        print("  2. ▶️ Démarrer daemon")
        print("  3. Change l'heure programmée pour l'heure actuelle +1min")
        print("  4. Attends...")
        print("  5. Check Telegram → message complet !")
        print()
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ ÉCHEC DU FIX AUTOMATIQUE")
        print("=" * 60)
        print()
        print("💡 Solution: Fix manuel")
        print("   python FIX_DAEMON_MANUEL.py")
        print()
        return 1


if __name__ == "__main__":
    exit(main())
