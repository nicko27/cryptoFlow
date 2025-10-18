"""
Classe de base pour les courtiers.
"""

from typing import Optional, Dict, Any

from core.models import MarketData, BrokerQuote


class Broker:
    """Interface minimale pour un courtier."""

    name: str = "Broker"
    slug: str = "broker"

    def supports(self, symbol: str) -> bool:
        """Vérifie si le courtier peut proposer ce symbole."""
        return True

    def get_quote(self, symbol: str, market_data: MarketData) -> Optional[BrokerQuote]:
        """Retourne la cotation achat/vente pour un symbole."""
        raise NotImplementedError

    def configure(self, settings: Dict[str, Any]) -> None:
        """Applique des réglages spécifiques au courtier."""
        # Implémentation optionnelle dans les sous-classes
        return None
