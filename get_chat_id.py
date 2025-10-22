#!/usr/bin/env python3
"""
Script pour obtenir votre TELEGRAM_CHAT_ID
Utilisation : python get_chat_id.py
"""

import requests
import json

# Remplacez par votre token
TELEGRAM_BOT_TOKEN = "7840017559:AAEdV7RHrxS_pog2S5yz9qsddF-Jr1EkMg0"

def get_updates():
    """Récupère les derniers messages reçus par le bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('ok'):
            print("❌ Erreur API Telegram")
            return
        
        updates = data.get('result', [])
        
        if not updates:
            print("⚠️  Aucun message trouvé")
            print("\n📱 ÉTAPES À SUIVRE:")
            print("1. Ouvrez Telegram")
            print("2. Cherchez @Crypto_Nicko_Bot")
            print("3. Envoyez /start au bot")
            print("4. Relancez ce script\n")
            return
        
        print("="*60)
        print("📋 MESSAGES REÇUS PAR LE BOT")
        print("="*60)
        
        chat_ids = set()
        
        for update in updates:
            message = update.get('message', {})
            chat = message.get('chat', {})
            from_user = message.get('from', {})
            text = message.get('text', '')
            
            chat_id = chat.get('id')
            username = from_user.get('username', 'Inconnu')
            first_name = from_user.get('first_name', '')
            
            if chat_id:
                chat_ids.add(chat_id)
                
                print(f"\n📨 Message de : @{username} ({first_name})")
                print(f"   💬 Texte     : {text}")
                print(f"   🔑 Chat ID   : {chat_id}")
                print(f"   📅 Date      : {message.get('date')}")
        
        if chat_ids:
            print("\n" + "="*60)
            print("✅ CHAT ID(S) TROUVÉ(S)")
            print("="*60)
            
            for chat_id in chat_ids:
                print(f"\n🔑 Utilisez ce Chat ID : {chat_id}")
                print(f"\nDans votre config/config.yaml :")
                print(f"telegram:")
                print(f"  chat_id: \"{chat_id}\"")
            
            print("\n" + "="*60)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
    except Exception as e:
        print(f"❌ Erreur : {e}")


if __name__ == "__main__":
    print("\n🤖 Récupération du Chat ID Telegram...\n")
    get_updates()
