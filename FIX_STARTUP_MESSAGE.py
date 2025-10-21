#!/usr/bin/env python3
"""
FIX MESSAGE DÉMARRAGE - Envoie un résumé complet au lieu d'une liste simple
"""

import shutil
from pathlib import Path
from datetime import datetime


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_startup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path("daemon/daemon_service.py")
    if src.exists():
        dst = backup_dir / "daemon_service.py"
        shutil.copy2(src, dst)
        print(f"✅ Sauvegarde: {backup_dir}")
    return backup_dir


def fix_startup_message():
    """Remplace _send_startup_message pour utiliser SummaryService"""
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return False
    
    content = file.read_text(encoding='utf-8')
    
    # Nouvelle implémentation
    new_startup = '''    def _send_startup_message(self):
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
                    "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\\n\\n"
                    f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\\n\\n"
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
                "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\\n"
                f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\\n\\n"
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
'''
    
    # Trouver et remplacer _send_startup_message
    import re
    pattern = r'    def _send_startup_message\(self\):.*?(?=\n    def |\Z)'
    
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        content = content[:match.start()] + new_startup + content[match.end():]
        file.write_text(content, encoding='utf-8')
        print("✅ Méthode _send_startup_message remplacée")
        return True
    else:
        print("⚠️ Méthode _send_startup_message non trouvée")
        return False


def main():
    print("=" * 60)
    print("🚀 FIX MESSAGE DÉMARRAGE")
    print("=" * 60)
    print()
    
    backup()
    print()
    
    print("📝 Modification du message de démarrage...")
    
    if fix_startup_message():
        print()
        print("=" * 60)
        print("✅ FIX APPLIQUÉ")
        print("=" * 60)
        print()
        print("🎯 Maintenant, au démarrage du daemon:")
        print("  • Message complet avec analyses")
        print("  • Prix, prédictions, opportunités")
        print("  • Format identique aux résumés programmés")
        print()
        print("🧪 Teste:")
        print("  1. python main.py")
        print("  2. ▶️ Démarrer daemon")
        print("  3. Check Telegram → message complet !")
        print()
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ ÉCHEC")
        print("=" * 60)
        print()
        print("💡 Modifie manuellement:")
        print("  1. Ouvre daemon/daemon_service.py")
        print("  2. Cherche: def _send_startup_message(self):")
        print("  3. Remplace par le code dans ce script")
        print()
        return 1


if __name__ == "__main__":
    exit(main())
