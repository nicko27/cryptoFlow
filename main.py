# Ajouter les imports
from core.services.database_service import DatabaseService
from core.services.portfolio_service import PortfolioService
from core.services.dca_service import DCAService
from core.services.report_service import ReportService
from core.services.chart_service import ChartService
from api.enhanced_telegram_api import EnhancedTelegramAPI
from core.services.summary_service import SummaryService

def run_gui_mode(config: BotConfiguration):
    # Initialiser les services
    db_service = DatabaseService(config.database_path)
    portfolio_service = PortfolioService()
    dca_service = DCAService()
    report_service = ReportService()
    chart_service = ChartService()
    telegram_api = EnhancedTelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
    summary_service = SummaryService(config)
    
    # Démarrer la queue Telegram
    telegram_api.start_queue()
    
    # Lancer GUI avec les nouveaux services
    from ui.main_window import CryptoBotGUI
    app = CryptoBotGUI(config, db_service, portfolio_service, dca_service, 
                       report_service, chart_service, telegram_api, summary_service)
    app.mainloop()
    
    # Arrêter la queue
    telegram_api.stop_queue()

def run_daemon_mode(config: BotConfiguration):
    from daemon.daemon_service import DaemonService
    print("🔄 Lancement démon...")
    daemon = DaemonService(config)
    daemon.start()

def run_once_mode(config: BotConfiguration, symbol: str = None):
    from api.binance_api import BinanceAPI
    from api.telegram_api import TelegramAPI
    from core.services.market_service import MarketService
    from core.services.alert_service import AlertService
    from core.models import AlertLevel
    
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION UNIQUE")
    print("="*60 + "\n")
    
    binance_api = BinanceAPI()
    telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
    market_service = MarketService(binance_api)
    alert_service = AlertService(config)
    
    symbols = [symbol] if symbol else config.crypto_symbols
    
    for sym in symbols:
        print(f"\n📊 {sym}:")
        print("-" * 60)
        try:
            market_data = market_service.get_market_data(sym)
            if not market_data:
                print("❌ Données indisponibles")
                continue
            
            prediction = market_service.predict_price_movement(market_data)
            opportunity = market_service.calculate_opportunity_score(market_data, prediction)
            
            print(f"💰 Prix: {market_data.current_price.price_eur:.2f} €")
            print(f"📈 Change 24h: {market_data.current_price.change_24h:+.2f}%")
            print(f"🎯 RSI: {market_data.technical_indicators.rsi:.0f}")
            print(f"\n🔮 Prédiction: {prediction.prediction_type.value}")
            print(f"   Confiance: {prediction.confidence}%")
            print(f"\n⭐ Score: {opportunity.score}/10")
            print(f"   {opportunity.recommendation}")
            
            if opportunity.reasons:
                print("\n💡 Raisons:")
                for reason in opportunity.reasons[:3]:
                    print(f"   • {reason}")
            
            alerts = alert_service.check_alerts(market_data, prediction)
            if alerts:
                print(f"\n🚨 Alertes ({len(alerts)}):")
                for alert in alerts:
                    print(f"   • [{alert.alert_level.value.upper()}] {alert.message}")
                    if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                        telegram_api.send_alert(alert)
            else:
                print("\nℹ️ Aucune alerte")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    print("\n" + "="*60 + "\n")

def setup_wizard():
    from config.setup_wizard import run_setup_wizard
    print("\n🎮 ASSISTANT DE CONFIGURATION\n")
    config = run_setup_wizard()
    print("\n✅ Configuration terminée!")
    print("\nCommandes:")
    print("  python main.py              # GUI")
    print("  python main.py --daemon     # Démon")
    print("  python main.py --once       # Test\n")
    return config

def main():
    parser = argparse.ArgumentParser(description="Crypto Bot v3.0 PyQt6")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--symbol", type=str)
    args = parser.parse_args()
    
    if args.setup:
        setup_wizard()
        sys.exit(0)
    
    try:
        config_manager = ConfigManager(args.config)
        if not config_manager.config_exists():
            print(f"❌ Config non trouvée: {args.config}")
            print("\n💡 Lancer: python main.py --setup\n")
            sys.exit(1)
        
        config = config_manager.load_config()
        
        if not config.telegram_bot_token or not config.telegram_chat_id:
            print("❌ Configuration Telegram invalide!")
            print("\n💡 Relancer: python main.py --setup\n")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur config: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🚀 CRYPTO BOT v3.0 PyQt6")
    print("="*60)
    print(f"Cryptos: {', '.join(config.crypto_symbols)}")
    print(f"Intervalle: {config.check_interval_seconds}s")
    print("="*60 + "\n")
    
    if args.once:
        run_once_mode(config, args.symbol)
    elif args.daemon:
        run_daemon_mode(config)
    else:
        run_gui_mode(config)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}\n")
        sys.exit(1)
