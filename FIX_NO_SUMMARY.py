#!/usr/bin/env python3
"""
FIX DÉMARRAGE - Force NotificationGenerator sans vérifier l'heure
Pour que le démarrage respecte aussi notifications.yaml
"""

import shutil
import re
from pathlib import Path
from datetime import datetime


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_startup_force_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    src = Path("daemon/daemon_service.py")
    if src.exists():
        shutil.copy2(src, backup_dir / "daemon_service.py")
        print(f"✅ Sauvegarde: {backup_dir}")
    return backup_dir


def fix_startup_message():
    """
    Modifie _send_startup_message pour FORCER l'utilisation de NotificationGenerator
    en utilisant la première config disponible (même si pas l'heure programmée)
    """
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return False
    
    content = file.read_text(encoding='utf-8')
    
    new_startup = '''    def _send_startup_message(self):
        """Envoie un message de démarrage selon notifications.yaml (FORCÉ)"""
        try:
            self.logger.info("📊 Génération du message de démarrage...")
            
            # En-tête de démarrage
            startup_header = (
                "🚀 <b>CRYPTO BOT DÉMARRÉ</b>\\n"
                f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\\n\\n"
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
                    from core.services.notification_generator import NotificationGenerator
                    
                    # Créer un générateur temporaire pour utiliser ses méthodes de blocs
                    temp_gen = NotificationGenerator(self.notification_settings, self.config.crypto_symbols)
                    
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
                        notification = "\\n\\n".join(message_parts)
                        all_notifications.append(notification)
                
                except Exception as e:
                    self.logger.error(f"Erreur notification {symbol}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            if not all_notifications:
                self.logger.warning("Aucune notification générée")
                return
            
            # Assembler et envoyer
            full_message = startup_header + "\\n\\n".join(all_notifications)
            
            success = self.telegram_api.send_message(full_message, parse_mode="HTML")
            
            if success:
                self.logger.info("✅ Message de démarrage envoyé (notifications.yaml respecté)")
            else:
                self.logger.error("❌ Échec envoi message de démarrage")
        
        except Exception as e:
            self.logger.error(f"❌ Erreur message démarrage: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
'''
    
    # Remplacer
    pattern = r'    def _send_startup_message\(self\):.*?(?=\n    def |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        content = content[:match.start()] + new_startup + content[match.end():]
        file.write_text(content, encoding='utf-8')
        print("✅ _send_startup_message remplacé")
        return True
    else:
        print("⚠️  _send_startup_message non trouvé")
        return False


def main():
    print("=" * 70)
    print("🚀 FIX DÉMARRAGE - FORCE NOTIFICATIONS.YAML")
    print("=" * 70)
    print()
    print("Ce fix fait en sorte que MÊME AU DÉMARRAGE,")
    print("le daemon utilise votre config notifications.yaml")
    print("avec les blocs que vous avez configurés.")
    print()
    print("FINI le SummaryService !")
    print()
    print("=" * 70)
    print()
    
    backup()
    print()
    
    if fix_startup_message():
        print()
        print("=" * 70)
        print("✅ FIX APPLIQUÉ")
        print("=" * 70)
        print()
        print("🎯 Maintenant:")
        print()
        print("  AU DÉMARRAGE:")
        print("    → Utilise notifications.yaml")
        print("    → BTC: header, prix, prédiction, opportunité, brokers, footer")
        print("    → ETH/SOL: header, prix, brokers, footer")
        print()
        print("  AUX HEURES PROGRAMMÉES:")
        print("    → Même chose (notifications.yaml)")
        print()
        print("  ❌ PLUS de SummaryService nulle part !")
        print()
        print("🧪 Teste:")
        print("  1. python main.py")
        print("  2. Démarre le daemon")
        print("  3. Check Telegram → format selon notifications.yaml")
        print()
        return 0
    else:
        print()
        print("=" * 70)
        print("❌ ÉCHEC")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit(main())
