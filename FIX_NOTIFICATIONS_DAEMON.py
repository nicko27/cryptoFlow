#!/usr/bin/env python3
"""
FIX NOTIFICATIONS DAEMON - Corrige le système de notifications
PROBLÈMES RÉSOLUS:
1. Brokers non affichés alors que configurés
2. Alertes envoyées alors que non demandées
3. Configuration YAML non respectée
"""

import shutil
from pathlib import Path
from datetime import datetime


def backup():
    """Crée une sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_notifications_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files = [
        "daemon/daemon_service.py",
        "core/services/notification_generator.py"
    ]
    
    for file in files:
        src = Path(file)
        if src.exists():
            dst = backup_dir / file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    print(f"✅ Sauvegarde: {backup_dir}")
    return backup_dir


def fix_daemon_check_cycle():
    """Corrige _check_cycle pour respecter la config et ne pas envoyer d'alertes séparées"""
    
    file = Path("daemon/daemon_service.py")
    if not file.exists():
        print("❌ daemon/daemon_service.py non trouvé")
        return False
    
    content = file.read_text(encoding='utf-8')
    
    # Nouvelle implémentation de _check_cycle
    new_check_cycle = '''    def _check_cycle(self):
        """Effectue un cycle de vérification - N'ENVOIE QUE LES NOTIFICATIONS CONFIGURÉES"""
        try:
            current_hour = datetime.now(timezone.utc).hour
            current_day = datetime.now(timezone.utc).weekday()
            
            # Vérifier si c'est l'heure d'envoyer un résumé
            should_send_summary = False
            if current_hour in self.config.summary_hours:
                if self.last_summary_sent is None or \\
                   (datetime.now(timezone.utc) - self.last_summary_sent).total_seconds() > 3000:
                    should_send_summary = True
            
            if not should_send_summary:
                # Pas l'heure programmée, ne rien envoyer
                return
            
            self.logger.info(f"\\n⏰ Heure programmée: {current_hour}h - Génération des notifications...")
            
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
'''
    
    # Trouver et remplacer _check_cycle
    import re
    
    # Pattern pour trouver toute la méthode _check_cycle
    pattern = r'    def _check_cycle\(self\):.*?(?=\n    def |\n\nclass |\Z)'
    
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        content = content[:match.start()] + new_check_cycle + content[match.end():]
        file.write_text(content, encoding='utf-8')
        print("✅ Méthode _check_cycle corrigée dans daemon_service.py")
        return True
    else:
        print("⚠️ _check_cycle non trouvé")
        return False


def create_example_notifications_yaml():
    """Crée un fichier notifications.yaml d'exemple avec tout désactivé sauf brokers"""
    
    yaml_content = '''# Configuration des notifications
# Activez/désactivez les blocs selon vos besoins

notifications:
  enabled: true
  kid_friendly_mode: true
  use_emojis_everywhere: true
  explain_everything: true
  respect_quiet_hours: true
  quiet_start: 23
  quiet_end: 7
  default_scheduled_hours: [9, 12, 18]

# Configuration par crypto
coins:
  BTC:
    enabled: true
    nickname: "Bitcoin"
    custom_emoji: "₿"
    
    scheduled_notifications:
      - name: "Notification principale"
        enabled: true
        hours: [9, 12, 18]
        days_of_week: [0, 1, 2, 3, 4, 5, 6]
        
        # Ordre d'affichage des blocs
        blocks_order:
          - header
          - price
          - prediction
          - opportunity
          - brokers      # ← ACTIVÉ
          - footer
        
        header_message: "🔔 {symbol} - Mise à jour"
        footer_message: "ℹ️ Ceci n'est pas un conseil financier"
        
        # Configuration de chaque bloc
        price_block:
          enabled: true
          show_price_eur: true
          show_variation_24h: true
          show_variation_7d: false
          show_volume: true
          show_market_cap: false
          add_price_comment: false
        
        chart_block:
          enabled: false  # ← DÉSACTIVÉ
        
        prediction_block:
          enabled: true
          show_prediction_type: true
          show_confidence: true
          min_confidence_to_show: 50
        
        opportunity_block:
          enabled: true
          show_score: true
          show_recommendation: true
          show_reasons: false
          min_score_to_show: 0
        
        brokers_block:
          enabled: true              # ← ACTIVÉ ICI
          title: "💱 Prix sur les brokers"
          show_best_price: true
          show_all_brokers: true
          show_fees: true
          max_brokers_displayed: 5
          explanation: "Comparaison des prix sur différentes plateformes"
        
        fear_greed_block:
          enabled: false  # ← DÉSACTIVÉ
        
        gain_loss_block:
          enabled: false  # ← DÉSACTIVÉ
        
        investment_suggestions_block:
          enabled: false  # ← DÉSACTIVÉ
        
        glossary_block:
          enabled: false  # ← DÉSACTIVÉ
  
  ETH:
    enabled: true
    nickname: "Ethereum"
    custom_emoji: "🦄"
    
    scheduled_notifications:
      - name: "Notification ETH"
        enabled: true
        hours: [9, 18]
        
        blocks_order:
          - header
          - price
          - brokers
          - footer
        
        price_block:
          enabled: true
        
        brokers_block:
          enabled: true
  
  SOL:
    enabled: true
    nickname: "Solana"
    custom_emoji: "⚡"
    
    scheduled_notifications:
      - name: "Notification SOL"
        enabled: true
        hours: [9, 18]
        
        blocks_order:
          - header
          - price
          - brokers
          - footer
        
        price_block:
          enabled: true
        
        brokers_block:
          enabled: true
'''
    
    file = Path("config/notifications_example_simple.yaml")
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(yaml_content, encoding='utf-8')
    
    print(f"✅ Exemple créé: {file}")
    print("\n💡 Pour utiliser cet exemple:")
    print("   cp config/notifications_example_simple.yaml config/notifications.yaml")


def show_instructions():
    """Affiche les instructions"""
    
    print("\n" + "="*70)
    print("📋 INSTRUCTIONS POST-FIX")
    print("="*70)
    print("\n1️⃣  CONFIGURATION DES NOTIFICATIONS")
    print("   • Éditez config/notifications.yaml")
    print("   • Activez UNIQUEMENT les blocs que vous voulez:")
    print("     - brokers_block: enabled: true   ← Pour les prix brokers")
    print("     - chart_block: enabled: false     ← Pas de graphiques")
    print("     - glossary_block: enabled: false  ← Pas de glossaire")
    print("\n2️⃣  DÉSACTIVER LES ALERTES")
    print("   • Le daemon n'enverra PLUS d'alertes séparées")
    print("   • Seules les notifications programmées seront envoyées")
    print("   • Pour réactiver: voir alert_service.py")
    print("\n3️⃣  TESTER")
    print("   • python main.py")
    print("   • Démarrer daemon")
    print("   • Modifier summary_hours dans config.yaml pour avoir l'heure actuelle")
    print("   • Attendre la prochaine notification")
    print("\n4️⃣  VÉRIFIER LE CONTENU")
    print("   • La notification doit contenir:")
    print("     ✓ Prix et variations (si price_block.enabled: true)")
    print("     ✓ Prix brokers (si brokers_block.enabled: true)")
    print("     ✗ PAS d'alertes séparées")
    print("     ✗ PAS de blocs désactivés")
    print("\n" + "="*70)


def main():
    print("\n" + "="*70)
    print("🔧 FIX NOTIFICATIONS DAEMON")
    print("="*70)
    print("\n📝 Problèmes à corriger:")
    print("  • Brokers non affichés")
    print("  • Alertes envoyées alors que non configurées")
    print("  • Configuration YAML non respectée")
    print()
    
    # Backup
    backup()
    print()
    
    # Corrections
    print("📝 Application des correctifs...")
    print()
    
    success = fix_daemon_check_cycle()
    
    if success:
        create_example_notifications_yaml()
        
        print()
        print("="*70)
        print("✅ CORRECTIFS APPLIQUÉS")
        print("="*70)
        
        show_instructions()
    else:
        print()
        print("="*70)
        print("❌ ÉCHEC")
        print("="*70)
        print("\n⚠️  Impossible de trouver _check_cycle à remplacer")
        print("💡 Veuillez vérifier manuellement daemon/daemon_service.py")
    
    print()


if __name__ == "__main__":
    main()
