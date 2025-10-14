"""
Main Entry Point - Crypto Bot v3.0
===================================

Point d'entrée principal avec support :
- Mode GUI (interface graphique)
- Mode daemon (arrière-plan)
- Mode once (exécution unique)
"""

import argparse
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from core.models import BotConfiguration
from config.config_manager import ConfigManager


def run_gui_mode(config: BotConfiguration):
    """Lance l'interface graphique"""
    try:
        from ui.main_window import CryptoBotGUI
        
        print("🚀 Lancement de l'interface graphique...")
        app = CryptoBotGUI(config)
        app.mainloop()
    
    except ImportError as e:
        print(f"❌ Erreur : dépendances manquantes pour le mode GUI")
        print(f"   Installe les dépendances : pip install -r requirements.txt")
        print(f"   Détail : {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Erreur lancement GUI : {e}")
        sys.exit(1)


def run_daemon_mode(config: BotConfiguration):
    """Lance en mode démon (arrière-plan)"""
    try:
        from daemon.daemon_service import DaemonService
        
        print("🔄 Lancement du démon...")
        daemon = DaemonService(config)
        daemon.start()
    
    except ImportError as e:
        print(f"❌ Erreur : module démon manquant")
        print(f"   Détail : {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Erreur lancement démon : {e}")
        sys.exit(1)


def run_once_mode(config: BotConfiguration, symbol: str = None):
    """Exécute une seule vérification"""
    from api.binance_api import BinanceAPI
    from api.telegram_api import TelegramAPI
    from core.services.market_service import MarketService
    from core.services.alert_service import AlertService
    
    print(f"\n{'='*60}")
    print(f"🔍 VÉRIFICATION UNIQUE")
    print(f"{'='*60}\n")
    
    # Services
    binance_api = BinanceAPI()
    telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
    market_service = MarketService(binance_api)
    alert_service = AlertService(config)
    
    # Symboles à vérifier
    symbols = [symbol] if symbol else config.crypto_symbols
    
    for sym in symbols:
        print(f"\n📊 {sym}:")
        print("-" * 60)
        
        try:
            # Récupérer données
            market_data = market_service.get_market_data(sym)
            if not market_data:
                print(f"❌ Impossible de récupérer les données")
                continue
            
            # Prédiction
            prediction = market_service.predict_price_movement(market_data)
            
            # Score opportunité
            opportunity = market_service.calculate_opportunity_score(market_data, prediction)
            
            # Afficher résumé
            print(f"💰 Prix actuel : {market_data.current_price.price_eur:.2f} €")
            print(f"📈 Changement 24h : {market_data.current_price.change_24h:+.2f}%")
            print(f"🎯 RSI : {market_data.technical_indicators.rsi:.0f}")
            
            if market_data.fear_greed_index:
                print(f"😱 Fear & Greed : {market_data.fear_greed_index}/100")
            
            print(f"\n🔮 Prédiction : {prediction.prediction_type.value}")
            print(f"   Confiance : {prediction.confidence}%")
            print(f"   Direction : {prediction.direction}")
            
            print(f"\n⭐ Score opportunité : {opportunity.score}/10")
            print(f"   {opportunity.recommendation}")
            
            if opportunity.reasons:
                print(f"\n💡 Raisons :")
                for reason in opportunity.reasons[:3]:
                    print(f"   • {reason}")
            
            # Vérifier alertes
            alerts = alert_service.check_alerts(market_data, prediction)
            
            if alerts:
                print(f"\n🚨 Alertes ({len(alerts)}) :")
                for alert in alerts:
                    print(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                    
                    # Envoyer sur Telegram
                    if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                        telegram_api.send_alert(alert)
            else:
                print(f"\nℹ️ Aucune alerte")
        
        except Exception as e:
            print(f"❌ Erreur : {e}")
    
    print(f"\n{'='*60}\n")


def setup_wizard():
    """Assistant de configuration initial"""
    from config.setup_wizard import run_setup_wizard
    
    print("\n" + "="*60)
    print("🎮 ASSISTANT DE CONFIGURATION")
    print("="*60 + "\n")
    
    config = run_setup_wizard()
    
    print("\n✅ Configuration terminée !")
    print("\nPour lancer le bot :")
    print("  • Mode GUI : python main.py")
    print("  • Mode démon : python main.py --daemon")
    print("  • Test : python main.py --once\n")
    
    return config


def main():
    """Point d'entrée principal"""
    
    parser = argparse.ArgumentParser(
        description="Crypto Bot v3.0 - Bot d'alertes crypto intelligent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python main.py                    Lance l'interface graphique
  python main.py --daemon          Lance en mode démon
  python main.py --once            Vérification unique
  python main.py --once --symbol BTC   Vérification unique pour BTC
  python main.py --setup           Configure le bot
        """
    )
    
    parser.add_argument("--gui", action="store_true", help="Lance l'interface graphique (défaut)")
    parser.add_argument("--daemon", action="store_true", help="Lance en mode démon")
    parser.add_argument("--once", action="store_true", help="Exécution unique")
    parser.add_argument("--setup", action="store_true", help="Lance l'assistant de configuration")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Fichier de configuration")
    parser.add_argument("--symbol", type=str, help="Symbole crypto (pour --once)")
    parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    
    args = parser.parse_args()
    
    # Mode setup
    if args.setup:
        config = setup_wizard()
        sys.exit(0)
    
    # Charger configuration
    try:
        config_manager = ConfigManager(args.config)
        
        if not config_manager.config_exists():
            print(f"❌ Fichier de configuration non trouvé : {args.config}")
            print(f"\n💡 Lance l'assistant de configuration :")
            print(f"   python main.py --setup\n")
            sys.exit(1)
        
        config = config_manager.load_config()
        
        # Valider config
        if not config.telegram_bot_token or not config.telegram_chat_id:
            print(f"❌ Configuration Telegram invalide !")
            print(f"\n💡 Relance l'assistant de configuration :")
            print(f"   python main.py --setup\n")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Erreur chargement configuration : {e}")
        sys.exit(1)
    
    # Bannière
    print("\n" + "="*60)
    print("🚀 CRYPTO BOT v3.0")
    print("="*60)
    print(f"Cryptos surveillées : {', '.join(config.crypto_symbols)}")
    print(f"Intervalle : {config.check_interval_seconds}s")
    print("="*60 + "\n")
    
    # Déterminer mode
    if args.once:
        run_once_mode(config, args.symbol)
    
    elif args.daemon:
        run_daemon_mode(config)
    
    else:
        # Par défaut : GUI
        run_gui_mode(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt du bot...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}\n")
        sys.exit(1)
