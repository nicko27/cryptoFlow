# Crypto Bot - Setup complet ✅

## Fichiers créés
- ✅ daemon/daemon_service.py (message démarrage enrichi)
- ✅ api/telegram_api.py (avec get_bot_info)
- ✅ api/binance_api.py
- ✅ api/revolut_api.py  
- ✅ core/models/__init__.py
- ✅ core/services/market_service.py
- ✅ core/services/alert_service.py
- ✅ utils/logger.py
- ✅ Tous les __init__.py

## Message Telegram au démarrage inclut:
📅 Date/heure
💱 Taux Revolut USD/EUR
💰 État marché (prix USD + EUR)
📊 RSI, F&G, changement 24h
🔮 Prédiction avec confiance
⭐ Score opportunité
🎯 Recommandation achat/vente + probabilité
📊 Niveaux configurés
⚙️ Configuration complète
🚧 Features à venir (graphiques, etc.)

## Pour tester:
```bash
python main.py --daemon
```

Le daemon devrait maintenant démarrer sans erreur et envoyer le message complet sur Telegram.
