#!/usr/bin/env python3
"""
FIX DAEMON - Corrige les notifications du daemon
Problème : Le daemon envoie uniquement des alertes (RSI, Fear&Greed)
Solution : Utiliser SummaryService pour envoyer des notifications complètes
"""

import shutil
from pathlib import Path
from datetime import datetime


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_daemon_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path("daemon/daemon_service.py")
    if src.exists():
        dst = backup_dir / "daemon_service.py"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    
    print(f"✅ Sauvegarde: {backup_dir}")


def fix_daemon_notifications():
    """Corrige le daemon pour envoyer des notifications complètes"""
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return
    
    content = file.read_text(encoding='utf-8')
    
    # Ajouter l'import de SummaryService
    if "from core.services.summary_service import SummaryService" not in content:
        # Trouver où ajouter l'import
        import_pos = content.find("from core.services.notification_generator import NotificationGenerator")
        if import_pos > 0:
            content = (
                content[:import_pos] +
                "from core.services.summary_service import SummaryService\n" +
                content[import_pos:]
            )
            print("✅ Import SummaryService ajouté")
    
    # Ajouter summary_service dans __init__
    if "self.summary_service = SummaryService" not in content:
        # Trouver la ligne après self.dca_service
        pos = content.find("self.dca_service = DCAService()")
        if pos > 0:
            line_end = content.find("\n", pos)
            content = (
                content[:line_end+1] +
                "        self.summary_service = SummaryService(config)\n" +
                content[line_end+1:]
            )
            print("✅ summary_service ajouté dans __init__")
    
    # Remplacer la méthode _check_cycle
    old_check_cycle_start = "    def _check_cycle(self):"
    old_check_cycle_end = "\n    def _is_night_mode(self):"
    
    new_check_cycle = '''    def _check_cycle(self):
        """Effectue un cycle de vérification avec notifications complètes"""
        try:
            current_hour = datetime.now(timezone.utc).hour
            current_day = datetime.now(timezone.utc).weekday()
            
            # Collecter les données pour toutes les cryptos
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            self.logger.info("\\n" + "="*60)
            self.logger.info(f"🔍 VÉRIFICATION #{self.checks_count + 1}")
            self.logger.info("="*60)
            
            # Récupérer les données pour chaque crypto
            for symbol in self.config.crypto_symbols:
                try:
                    self.logger.info(f"\\n📊 {symbol}:")
                    self.logger.info("-"*60)
                    
                    # Récupérer les données de marché
                    market_data = self.market_service.get_market_data(symbol)
                    
                    if not market_data:
                        self.logger.warning(f"⚠️ Impossible de récupérer les données pour {symbol}")
                        continue
                    
                    markets_data[symbol] = market_data
                    
                    # Prédiction
                    prediction = self.market_service.predict_price_movement(market_data)
                    if prediction:
                        predictions[symbol] = prediction
                        self.logger.info(
                            f"🔮 Prédiction : {prediction.prediction_type.value.upper()} "
                            f"({prediction.confidence:.0f}%)"
                        )
                    
                    # Opportunité
                    opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                    if opportunity:
                        opportunities[symbol] = opportunity
                        self.logger.info(f"⭐ Opportunité : {opportunity.score}/10")
                    
                    # Sauvegarder en base
                    self.db_service.save_market_data(market_data)
                    if prediction:
                        self.db_service.save_prediction(symbol, prediction)
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur traitement {symbol}: {e}")
                    self.consecutive_errors += 1
            
            # Incrémenter le compteur
            self.checks_count += 1
            
            # Vérifier s'il faut envoyer un résumé
            should_send = False
            
            # Vérifier si on est à une heure programmée
            if current_hour in self.config.summary_hours:
                # Vérifier si on n'a pas déjà envoyé dans cette heure
                if self.last_summary_sent is None or \\
                   (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
                    should_send = True
                    self.logger.info(f"⏰ Heure programmée détectée: {current_hour}h")
            
            # Envoyer le résumé si nécessaire
            if should_send and markets_data:
                try:
                    self.logger.info("\\n📤 Génération et envoi du résumé...")
                    
                    # Générer le résumé via SummaryService
                    summary = self.summary_service.generate_summary(
                        markets_data,
                        predictions,
                        opportunities,
                        simple=self.config.use_simple_language
                    )
                    
                    if summary:
                        # Envoyer sur Telegram
                        success = self.telegram_api.send_message(summary, parse_mode="HTML")
                        
                        if success:
                            self.notifications_sent += 1
                            self.last_summary_sent = datetime.now(timezone.utc)
                            self.logger.info("✅ Résumé envoyé avec succès")
                        else:
                            self.logger.error("❌ Échec envoi résumé")
                    else:
                        self.logger.warning("⚠️ Aucun résumé généré")
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur envoi résumé: {e}")
            
            # Vérifier les alertes pour chaque crypto
            for symbol in self.config.crypto_symbols:
                if symbol not in markets_data:
                    continue
                
                try:
                    market_data = markets_data[symbol]
                    prediction = predictions.get(symbol)
                    
                    # Vérifier les alertes
                    alerts = self.alert_service.check_alerts(market_data, prediction)
                    
                    if alerts:
                        self.logger.info(f"\\n🚨 {len(alerts)} alerte(s) détectée(s) pour {symbol}:")
                        for alert in alerts:
                            # Envoyer chaque alerte
                            try:
                                self.telegram_api.send_alert(alert)
                                self.alerts_sent += 1
                                self.logger.info(f"   ✓ Alerte envoyée: {alert.message}")
                            except Exception as e:
                                self.logger.error(f"❌ Erreur envoi alerte: {e}")
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur vérification alertes {symbol}: {e}")
            
            # Stats
            if self.start_time:
                uptime = datetime.now(timezone.utc) - self.start_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                
                self.logger.info(
                    f"\\n📊 Stats : {self.checks_count} vérifications, "
                    f"{self.alerts_sent} alertes, {self.notifications_sent} notifications, "
                    f"{self.errors_count} erreurs ({self.consecutive_errors} consécutives), "
                    f"Uptime: {hours}h{minutes}m"
                )
            
            # Réinitialiser le compteur d'erreurs consécutives si tout s'est bien passé
            if markets_data:
                self.consecutive_errors = 0
        
        except Exception as e:
            self.logger.error(f"❌ Erreur cycle : {e}", exc_info=True)
            self.errors_count += 1
            self.consecutive_errors += 1
'''
    
    # Trouver et remplacer
    start_pos = content.find(old_check_cycle_start)
    end_pos = content.find(old_check_cycle_end)
    
    if start_pos > 0 and end_pos > start_pos:
        content = content[:start_pos] + new_check_cycle + content[end_pos:]
        file.write_text(content, encoding='utf-8')
        print("✅ Méthode _check_cycle remplacée")
    else:
        print("⚠️ Impossible de trouver _check_cycle à remplacer")


def main():
    print("=" * 60)
    print("🔧 FIX DAEMON - Notifications complètes")
    print("=" * 60)
    print()
    
    backup()
    print()
    
    print("📝 Corrections...")
    fix_daemon_notifications()
    
    print()
    print("=" * 60)
    print("✅ TERMINÉ")
    print("=" * 60)
    print()
    print("🎯 Ce qui change :")
    print("  • Daemon utilise maintenant SummaryService")
    print("  • Messages complets avec prix, prédictions, opportunités")
    print("  • Alertes envoyées séparément si nécessaire")
    print("  • Format cohérent avec le bouton résumé")
    print()
    print("🧪 Teste :")
    print("  python main.py")
    print("  ▶️ Démarrer daemon")
    print("  Attends la prochaine heure programmée (ex: 20:00)")
    print()


if __name__ == "__main__":
    main()
