"""
Core Package - Modules centraux du bot crypto
"""

from core.models import (
    BotConfiguration, CryptoPrice, MarketData,
    Alert, AlertType, AlertLevel,
    Prediction, PredictionType, OpportunityScore,
    TechnicalIndicators, PriceLevel
)

__version__ = "3.0.0"
__all__ = [
    "BotConfiguration", "CryptoPrice", "MarketData",
    "Alert", "AlertType", "AlertLevel",
    "Prediction", "PredictionType", "OpportunityScore",
    "TechnicalIndicators", "PriceLevel"
]
