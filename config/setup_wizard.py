"""
Setup Wizard - Assistant de configuration interactif
"""

import sys
from pathlib import Path
from typing import Dict, Any
from core.models import BotConfiguration
from config.config_manager import ConfigManager


def print_banner():
    """Affiche la bannière"""
    print("\n" + "="*70)
    print("🎮 CRYPTO BOT v3.0 - ASSISTANT DE CONFIGURATION")
    print("="*70 + "\n")


def print_section(title: str):
    """Affiche un titre de section"""
    print(f"\n{'─'*70}")
    print(f"📋 {title}")
    print(f"{'─'*70}\n")


def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    """Récupère une entrée utilisateur"""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                return default
            return user_input
        else:
            user_input = input(f"{prompt}: ").strip()
            if user_input or not required:
                return user_input
            print("❌ Ce champ est obligatoire!")


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Question oui/non"""
    default_text = "O/n" if default else "o/N"
    response = input(f"{prompt} [{default_text}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['o', 'oui', 'y', 'yes']


def get_number(prompt: str, default: float, min_val: float = None, max_val: float = None) -> float:
    """Récupère un nombre"""
    while True:
        try:
            response = input(f"{prompt} [{default}]: ").strip()
            value = float(response) if response else default
            
            if min_val is not None and value < min_val:
                print(f"❌ La valeur doit être >= {min_val}")
                continue
            
            if max_val is not None and value > max_val:
                print(f"❌ La valeur doit être <= {max_val}")
                continue
            
            return value
        
        except ValueError:
            print("❌ Veuillez entrer un nombre valide!")


def setup_telegram() -> Dict[str, str]:
    """Configure Telegram"""
    print_section("CONFIGURATION TELEGRAM")
    
    print("Pour créer un bot Telegram:")
    print("1. Ouvre Telegram et cherche @BotFather")
    print("2. Envoie /newbot et suis les instructions")
    print("3. Note le token du bot\n")
    
    bot_token = get_input("Token du bot Telegram", required=True)
    
    print("\nPour obtenir ton Chat ID:")
    print("1. Ouvre Telegram et cherche @userinfobot")
    print("2. Envoie /start")
    print("3. Note ton ID\n")
    
    chat_id = get_input("Ton Chat ID Telegram", required=True)
    
    return {
        "bot_token": bot_token,
        "chat_id": chat_id
    }


def setup_cryptos() -> Dict[str, Any]:
    """Configure les cryptos"""
    print_section("CRYPTOMONNAIES")
    
    print("Cryptos disponibles:")
    print("  • BTC (Bitcoin)")
    print("  • ETH (Ethereum)")
    print("  • SOL (Solana)")
    print("  • BNB (Binance Coin)")
    print("  • XRP (Ripple)")
    print("  • ADA (Cardano)")
    print("  • DOGE (Dogecoin)")
    print("  • AVAX (Avalanche)")
    print("  • DOT (Polkadot)")
    print("  • MATIC (Polygon)\n")
    
    symbols_input = get_input("Cryptos à surveiller (séparées par des virgules)", "BTC,ETH,SOL")
    symbols = [s.strip().upper() for s in symbols_input.split(",")]
    
    investment = get_number("Montant de référence pour calculs (€)", 100.0, min_val=1.0)
    
    return {
        "symbols": symbols,
        "investment_amount": investment
    }


def setup_alerts() -> Dict[str, Any]:
    """Configure les alertes"""
    print_section("ALERTES")
    
    enable = get_yes_no("Activer les alertes automatiques?", True)
    
    if not enable:
        return {"enable": False}
    
    print("\n📊 Seuils d'alertes:")
    drop_threshold = get_number("  Seuil de baisse (%)", 10.0, min_val=1.0)
    spike_threshold = get_number("  Seuil de hausse (%)", 10.0, min_val=1.0)
    lookback = get_number("  Période de référence (minutes)", 120, min_val=15)
    
    return {
        "enable": enable,
        "drop_threshold": drop_threshold,
        "spike_threshold": spike_threshold,
        "lookback_minutes": int(lookback)
    }


def setup_price_levels(symbols: list) -> Dict[str, Any]:
    """Configure les niveaux de prix"""
    print_section("NIVEAUX DE PRIX")
    
    enable = get_yes_no("Configurer des niveaux de prix d'alerte?", True)
    
    if not enable:
        return {"enable": False, "levels": {}}
    
    levels = {}
    
    print("\n💡 Les niveaux permettent d'être alerté quand le prix franchit un seuil.")
    print("Exemple: Alertes si BTC < 90000€ ou BTC > 105000€\n")
    
    for symbol in symbols:
        if get_yes_no(f"Configurer des niveaux pour {symbol}?", True):
            levels[symbol] = {}
            
            if get_yes_no(f"  Définir un niveau BAS pour {symbol}?", True):
                low = get_number(f"  Niveau BAS pour {symbol} (€)", 80000 if symbol == "BTC" else 3000)
                levels[symbol]["low"] = low
            
            if get_yes_no(f"  Définir un niveau HAUT pour {symbol}?", True):
                high = get_number(f"  Niveau HAUT pour {symbol} (€)", 105000 if symbol == "BTC" else 4000)
                levels[symbol]["high"] = high
    
    buffer = get_number("\nZone tampon autour des niveaux (€)", 2.0, min_val=0.1)
    
    return {
        "enable": enable,
        "levels": levels,
        "buffer_eur": buffer,
        "cooldown_minutes": 30
    }


def setup_features() -> Dict[str, Any]:
    """Configure les fonctionnalités"""
    print_section("FONCTIONNALITÉS INTELLIGENTES")
    
    print("Le bot peut fournir:")
    print("  • Score d'opportunité (0-10)")
    print("  • Prédictions (haussier/baissier)")
    print("  • Timeline de prédictions")
    print("  • Calcul de gains/pertes")
    print("  • Suggestions d'achat échelonné (DCA)")
    print()
    
    opportunity = get_yes_no("Activer le score d'opportunité?", True)
    predictions = get_yes_no("Activer les prédictions?", True)
    simple_language = get_yes_no("Utiliser un langage simple?", True)
    
    return {
        "opportunity_score": opportunity,
        "opportunity_threshold": 7,
        "predictions": predictions,
        "timeline": True,
        "gain_loss_calc": True,
        "dca_suggestions": True,
        "simple_language": simple_language,
        "educational_mode": True
    }


def setup_timing() -> Dict[str, Any]:
    """Configure les intervalles"""
    print_section("TIMING")
    
    print("Intervalles recommandés:")
    print("  • 300s (5 min)   - Surveillance très active")
    print("  • 900s (15 min)  - Usage normal [RECOMMANDÉ]")
    print("  • 1800s (30 min) - Surveillance passive")
    print("  • 3600s (1h)     - Surveillance minimale\n")
    
    interval = get_number("Intervalle entre vérifications (secondes)", 900, min_val=60)
    
    quiet_hours = get_yes_no("\nActiver le mode nuit (heures silencieuses)?", False)
    
    if quiet_hours:
        quiet_start = get_number("Heure de début du mode nuit (0-23)", 23, min_val=0, max_val=23)
        quiet_end = get_number("Heure de fin du mode nuit (0-23)", 7, min_val=0, max_val=23)
        allow_critical = get_yes_no("Autoriser les alertes critiques en mode nuit?", True)
    else:
        quiet_start = 23
        quiet_end = 7
        allow_critical = True
    
    return {
        "check_interval": int(interval),
        "summary_hours": [9, 12, 18],
        "quiet_hours": {
            "enable": quiet_hours,
            "start": int(quiet_start),
            "end": int(quiet_end),
            "allow_critical": allow_critical
        }
    }


def setup_mode() -> Dict[str, str]:
    """Configure le mode d'exécution"""
    print_section("MODE D'EXÉCUTION")
    
    print("Modes disponibles:")
    print("  • GUI    - Interface graphique [RECOMMANDÉ]")
    print("  • Daemon - Arrière-plan (serveur)")
    print()
    
    use_gui = get_yes_no("Utiliser l'interface graphique?", True)
    
    print("\nNiveaux de détail:")
    print("  • simple - Langage enfant, recommandations claires")
    print("  • normal - Équilibré [RECOMMANDÉ]")
    print("  • expert - Tous les détails techniques")
    print()
    
    detail = get_input("Niveau de détail", "normal")
    while detail not in ["simple", "normal", "expert"]:
        print("❌ Choisir: simple, normal ou expert")
        detail = get_input("Niveau de détail", "normal")
    
    return {
        "daemon": not use_gui,
        "gui": use_gui,
        "detail_level": detail
    }


def confirm_config(config_dict: Dict[str, Any]) -> bool:
    """Confirme la configuration"""
    print_section("RÉCAPITULATIF")
    
    print(f"Telegram:")
    print(f"  • Bot configuré: ✓")
    print(f"  • Chat ID: {config_dict['telegram']['chat_id']}\n")
    
    print(f"Cryptos: {', '.join(config_dict['crypto']['symbols'])}")
    print(f"Montant de référence: {config_dict['crypto']['investment_amount']}€\n")
    
    print(f"Alertes: {'✓ Activées' if config_dict['alerts']['enable'] else '✗ Désactivées'}")
    if config_dict['alerts']['enable']:
        print(f"  • Seuil baisse: {config_dict['alerts']['drop_threshold']}%")
        print(f"  • Seuil hausse: {config_dict['alerts']['spike_threshold']}%\n")
    
    if config_dict['price_levels']['enable']:
        print(f"Niveaux de prix: ✓ Configurés")
        for symbol, levels in config_dict['price_levels']['levels'].items():
            if levels:
                print(f"  • {symbol}: {levels}\n")
    
    print(f"Intervalle: {config_dict['timing']['check_interval']}s")
    print(f"Mode: {'GUI' if config_dict['mode']['gui'] else 'Daemon'}")
    print(f"Détail: {config_dict['mode']['detail_level']}\n")
    
    return get_yes_no("Confirmer cette configuration?", True)


def run_setup_wizard() -> BotConfiguration:
    """Lance l'assistant de configuration"""
    print_banner()
    
    print("Cet assistant va te guider pour configurer ton bot crypto.\n")
    print("💡 Tu peux appuyer sur Entrée pour utiliser les valeurs par défaut.\n")
    
    if not get_yes_no("Continuer?", True):
        print("\n👋 Configuration annulée.\n")
        sys.exit(0)
    
    # Collecte des infos
    telegram_config = setup_telegram()
    crypto_config = setup_cryptos()
    alerts_config = setup_alerts()
    price_levels_config = setup_price_levels(crypto_config["symbols"])
    features_config = setup_features()
    timing_config = setup_timing()
    mode_config = setup_mode()
    
    # Construire le dictionnaire complet
    full_config = {
        "telegram": telegram_config,
        "crypto": crypto_config,
        "alerts": alerts_config,
        "price_levels": price_levels_config,
        "features": features_config,
        "timing": timing_config,
        "display": {
            "graphs": True,
            "show_levels": True,
            "startup_summary": True
        },
        "mode": mode_config,
        "logging": {
            "file": "logs/crypto_bot.log",
            "level": "INFO"
        },
        "database": {
            "path": "data/crypto_bot.db",
            "keep_days": 30
        }
    }
    
    # Confirmer
    if not confirm_config(full_config):
        print("\n🔄 Recommence la configuration...\n")
        return run_setup_wizard()
    
    # Sauvegarder
    config_manager = ConfigManager("config/config.yaml")
    bot_config = config_manager._dict_to_config(full_config)
    
    try:
        config_manager.save_config(bot_config)
        print("\n✅ Configuration sauvegardée dans: config/config.yaml")
    except Exception as e:
        print(f"\n❌ Erreur sauvegarde: {e}")
        sys.exit(1)
    
    return bot_config


if __name__ == "__main__":
    run_setup_wizard()
