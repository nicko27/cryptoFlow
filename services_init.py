"""
Initialisation des services [AVEC REVOLUT ET TIMEZONE FIX]
"""

from api.binance_api import BinanceAPI
from api.revolut_api import RevolutAPI
from api.telegram_api import TelegramAPI
from core.services.market_service import MarketService
from core.services.alert_service import AlertService


def init_services(config):
    """
    Initialise tous les services avec Revolut intégré
    
    Args:
        config: BotConfiguration
    
    Returns:
        Dict avec tous les services
    """
    # 1. Créer Revolut API
    revolut_api = RevolutAPI()
    
    # 2. Créer Binance API avec Revolut
    binance_api = BinanceAPI(revolut_api=revolut_api)
    
    # 3. Créer autres services
    telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
    market_service = MarketService(binance_api)
    alert_service = AlertService(config)
    
    return {
        'revolut': revolut_api,
        'binance': binance_api,
        'telegram': telegram_api,
        'market': market_service,
        'alert': alert_service
    }


# Exemple d'utilisation dans main.py ou daemon
"""
from services_init import init_services

# Dans votre code
services = init_services(config)
market_service = services['market']
telegram_api = services['telegram']
...
"""
