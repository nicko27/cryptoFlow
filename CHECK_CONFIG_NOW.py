#!/usr/bin/env python3
"""
Vérifie l'état actuel de notifications.yaml
"""

import yaml
from pathlib import Path


def check_config():
    print("=" * 70)
    print("🔍 VÉRIFICATION CONFIG ACTUELLE")
    print("=" * 70)
    print()
    
    file = Path("config/notifications.yaml")
    
    if not file.exists():
        print("❌ config/notifications.yaml n'existe pas !")
        return
    
    with open(file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    print("📄 Structure détectée:")
    print()
    
    if 'coins' in data:
        print("✅ Section 'coins' présente")
        print()
        
        for symbol, config in data['coins'].items():
            print(f"  📊 {symbol}:")
            
            if 'scheduled_notifications' in config:
                notifs = config['scheduled_notifications']
                print(f"     • {len(notifs)} notification(s) programmée(s)")
                
                for i, notif in enumerate(notifs):
                    print(f"\n     Notification #{i+1}:")
                    print(f"       - name: {notif.get('name', '?')}")
                    print(f"       - enabled: {notif.get('enabled', '?')}")
                    print(f"       - hours: {notif.get('hours', '?')}")
                    
                    if 'blocks_order' in notif:
                        print(f"       - blocks_order: {notif['blocks_order']}")
                    else:
                        print("       ⚠️  AUCUN blocks_order défini !")
                    
                    # Vérifier les blocs individuels
                    print("\n       Blocs activés:")
                    for block_type in ['price_block', 'chart_block', 'prediction_block', 
                                      'opportunity_block', 'brokers_block', 'fear_greed_block',
                                      'gain_loss_block', 'investment_suggestions_block', 'glossary_block']:
                        if block_type in notif:
                            enabled = notif[block_type].get('enabled', False)
                            status = "✅" if enabled else "❌"
                            print(f"         {status} {block_type}: {enabled}")
            else:
                print("     ⚠️  Aucune notification programmée")
            
            print()
    else:
        print("❌ PAS de section 'coins' !")
        print("   → Config au format simplifié (écrasée par le GUI ?)")
        print()
        print("📄 Contenu actuel:")
        print(yaml.dump(data, default_flow_style=False, allow_unicode=True))


if __name__ == "__main__":
    check_config()
