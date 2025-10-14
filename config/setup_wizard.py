"""Setup Wizard - Assistant de configuration"""
import sys
from pathlib import Path
from core.models import BotConfiguration
from config.config_manager import ConfigManager

def print_banner():
    print("\n" + "="*70)
    print("🎮 CRYPTO BOT v3.0 - ASSISTANT DE CONFIGURATION")
    print("="*70 + "\n")

def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input if user_input else default
        user_input = input(f"{prompt}: ").strip()
        if user_input or not required:
            return user_input
        print("❌ Ce champ est obligatoire!")

def get_yes_no(prompt: str, default: bool = True) -> bool:
    default_text = "O/n" if default else "o/N"
    response = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not response:
        return default
    return response in ['o', 'oui', 'y', 'yes']

def run_setup_wizard() -> BotConfiguration:
    print_banner()
    print("Cet assistant va te guider pour configurer ton bot crypto.\n")
    
    bot_token = get_input("Token du bot Telegram", required=True)
    chat_id = get_input("Ton Chat ID Telegram", required=True)
    
    symbols_input = get_input("Cryptos à surveiller (séparées par virgules)", "BTC,ETH,SOL")
    symbols = [s.strip().upper() for s in symbols_input.split(",")]
    
    config_dict = {
        "telegram": {"bot_token": bot_token, "chat_id": chat_id},
        "crypto": {"symbols": symbols, "investment_amount": 100.0},
        "alerts": {"enable": True, "lookback_minutes": 120, "drop_threshold": 10.0, "spike_threshold": 10.0},
        "price_levels": {"enable": True, "levels": {}, "buffer_eur": 2.0, "cooldown_minutes": 30},
        "timing": {"check_interval": 900},
        "logging": {"file": "logs/crypto_bot.log", "level": "INFO"}
    }
    
    config_manager = ConfigManager("config/config.yaml")
    bot_config = config_manager._dict_to_config(config_dict)
    
    try:
        config_manager.save_config(bot_config)
        print("\n✅ Configuration sauvegardée !")
    except Exception as e:
        print(f"\n❌ Erreur sauvegarde: {e}")
        sys.exit(1)
    
    return bot_config
