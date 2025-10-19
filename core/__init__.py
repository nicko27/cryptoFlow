"""
Core Package - Modules centraux du bot crypto
FIXED: Problème 16 - Imports optimisés pour éviter les dépendances circulaires
"""

# FIXED: Import lazy pour éviter les imports circulaires
# Les imports sont effectués uniquement quand nécessaire

__version__ = "4.0.0"

# Liste des modules disponibles sans les importer directement
__all__ = [
    "BotConfiguration",
    "CryptoPrice",
    "MarketData",
    "Alert",
    "AlertType",
    "AlertLevel",
    "Prediction",
    "PredictionType",
    "OpportunityScore",
    "TechnicalIndicators",
    "PriceLevel",
]


def __getattr__(name):
    """
    FIXED: Problème 16 - Import lazy pour éviter les imports circulaires
    Charge les modules à la demande
    """
    if name in __all__:
        # Import à la demande depuis core.models
        from core import models
        return getattr(models, name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
