import argparse
import sys
from typing import Optional

from config.config_manager import ConfigManager
from core.models import BotConfiguration
from utils.logger import setup_logger


def _load_configuration(path: str) -> Optional[BotConfiguration]:
    """Charge la configuration YAML et gère les incohérences connues."""
    config_manager = ConfigManager(path)

    if not config_manager.config_exists():
        print(f"❌ Config non trouvée: {path}")
        print("\n💡 Lancer: python main.py --setup\n")
        return None

    try:
        return config_manager.load_config()
    except TypeError as exc:
        print(f"❌ Erreur config (structure incompatible): {exc}")
        print("   Vérifiez que core/models/BotConfiguration correspond au YAML.")
        return None
    except Exception as exc:
        print(f"❌ Erreur config: {exc}")
        return None


def run_gui_mode(config: BotConfiguration) -> None:
    """
    Lance l'application en mode GUI.
    Les imports sont locaux pour éviter les erreurs lorsque des dépendances
    optionnelles ne sont pas disponibles.
    """
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as exc:
        print(f"❌ PyQt6 est requis pour le mode GUI: {exc}")
        sys.exit(1)

    try:
        from ui.main_window import CryptoBotGUI
    except ImportError as exc:
        print(f"❌ Impossible de charger l'interface graphique: {exc}")
        sys.exit(1)

    qt_app = QApplication.instance() or QApplication(sys.argv)
    window = CryptoBotGUI()
    window.show()

    try:
        qt_app.exec()
    except Exception as exc:
        print(f"❌ Erreur GUI: {exc}")
        sys.exit(1)


def run_daemon_mode(config: BotConfiguration) -> None:
    """Démarre le daemon en mode headless."""
    try:
        from daemon.daemon_service import DaemonService
    except ImportError as exc:
        print(f"❌ Mode démon indisponible: {exc}")
        sys.exit(1)

    print("🔄 Lancement démon...")
    daemon = DaemonService(config)
    try:
        daemon.start()
    except Exception as exc:
        print(f"❌ Erreur lors du démarrage du démon: {exc}")
        sys.exit(1)


def run_once_mode(config: BotConfiguration, symbol: Optional[str] = None) -> None:
    """Effectue une vérification unique depuis la ligne de commande."""
    try:
        from api.binance_api import BinanceAPI
        from api.telegram_api import TelegramAPI
        from core.services.market_service import MarketService
        from core.services.alert_service import AlertService
        from core.models import AlertLevel
    except ImportError as exc:
        print(f"❌ Mode 'once' indisponible: {exc}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🔍 VÉRIFICATION UNIQUE")
    print("=" * 60 + "\n")

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
        except Exception as exc:
            print(f"❌ Erreur: {exc}")
    print("\n" + "=" * 60 + "\n")


def setup_wizard() -> BotConfiguration:
    """Exécute l'assistant de configuration interactif."""
    from config.setup_wizard import run_setup_wizard

    print("\n🎮 ASSISTANT DE CONFIGURATION\n")
    config = run_setup_wizard()
    print("\n✅ Configuration terminée!")
    print("\nCommandes:")
    print("  python main.py              # GUI")
    print("  python main.py --daemon     # Démon")
    print("  python main.py --once       # Test\n")
    return config


def main() -> None:
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

    config = _load_configuration(args.config)
    if config is None:
        sys.exit(1)

    if not config.telegram_bot_token or not config.telegram_chat_id:
        print("❌ Configuration Telegram invalide!")
        print("\n💡 Relancer: python main.py --setup\n")
        sys.exit(1)

    logger = setup_logger(
        name="CryptoBotCLI",
        log_file=config.log_file,
        level=config.log_level,
    )
    logger.info("Configuration chargée depuis %s", args.config)

    print("\n" + "=" * 60)
    print("🚀 CRYPTO BOT v3.0 PyQt6")
    print("=" * 60)
    print("=" * 60)
    print(f"Cryptos: {', '.join(config.crypto_symbols)}")
    print(f"Intervalle: {config.check_interval_seconds}s")
    print("=" * 60 + "\n")

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
    except Exception as exc:
        print(f"\n❌ Erreur fatale: {exc}\n")
        sys.exit(1)
