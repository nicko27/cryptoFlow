#!/usr/bin/env python3
"""
Ajoute les emojis manquants dans core/constants/emojis.py
"""

import os
import sys

def add_missing_emojis():
    """Ajoute tous les emojis manquants"""
    
    filepath = "core/constants/emojis.py"
    
    if not os.path.exists(filepath):
        print(f"❌ Fichier non trouvé : {filepath}")
        return False
    
    print(f"🔧 Ajout des emojis manquants dans {filepath}...\n")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup
        backup = filepath + ".backup"
        with open(backup, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Backup : {backup}")
        
        # Ajouter les emojis manquants après la section "Autres"
        additional_emojis = '''
    # Prédictions détaillées
    BULLISH = "🚀"
    BEARISH = "📉"
    NEUTRAL = "➡️"
    
    # Courtiers et plateformes
    BROKER = "🏦"
    EXCHANGE = "💱"
    
    # Sentiments
    SENTIMENT = "😊"
    FEAR = "😰"
    GREED = "🤑"
    
    # Gains et pertes
    GAIN = "💰"
    LOSS = "📉"
    PROFIT = "💵"
    
    # Suggestions
    SUGGESTION = "💡"
    IDEA = "🧠"
    TIP = "👉"
'''
        
        # Vérifier si déjà ajoutés
        if 'BULLISH' in content:
            print("ℹ️  Les emojis sont déjà présents")
            return True
        
        # Trouver où insérer (avant les méthodes statiques)
        insert_pos = content.find('    @staticmethod')
        
        if insert_pos == -1:
            # Si pas de @staticmethod, insérer avant la fin de la classe
            insert_pos = content.rfind('\n\n')
        
        # Insérer les emojis
        new_content = content[:insert_pos] + additional_emojis + '\n' + content[insert_pos:]
        
        # Sauvegarder
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✓ Emojis ajoutés :")
        print("  • BULLISH, BEARISH, NEUTRAL")
        print("  • BROKER, EXCHANGE")
        print("  • SENTIMENT, FEAR, GREED")
        print("  • GAIN, LOSS, PROFIT")
        print("  • SUGGESTION, IDEA, TIP")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🔧 AJOUT DES EMOJIS MANQUANTS")
    print("="*70 + "\n")
    
    if not os.path.exists("core/constants"):
        print("❌ Répertoire core/constants/ non trouvé")
        return False
    
    success = add_missing_emojis()
    
    if success:
        print("\n✅ Emojis ajoutés avec succès !")
        print("\n🎯 Redémarrez le bot pour appliquer :")
        print("   python3 main.py --daemon")
    else:
        print("\n❌ Échec de l'ajout")
    
    print("\n" + "="*70 + "\n")
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
