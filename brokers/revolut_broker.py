"""
Courtier Revolut - approximation des prix achat/vente avec spread et frais.
"""

from typing import Optional

from brokers.base import Broker
from core.models import MarketData, BrokerQuote


class RevolutBroker(Broker):
    name = "Revolut"
    slug = "revolut"
    spread_pct = 0.005  # 0,5% de spread
    fee_pct = 0.015  # 1,5% de frais par transaction

    def configure(self, settings: dict) -> None:
        if not settings:
            return
        spread = settings.get("spread_pct")
        fee = settings.get("fee_pct")
        if isinstance(spread, (int, float)) and spread >= 0:
            self.spread_pct = float(spread)
        if isinstance(fee, (int, float)) and fee >= 0:
            self.fee_pct = float(fee)

    def get_quote(self, symbol: str, market_data: MarketData) -> Optional[BrokerQuote]:
        price = (
            market_data.current_price.price_eur
            if market_data.current_price and market_data.current_price.price_eur is not None
            else None
        )
        if price is None:
            return None

        # Spread appliqué au prix médian
        spread_buy = price * (1 + self.spread_pct)
        spread_sell = price * (1 - self.spread_pct)

        buy_price = spread_buy * (1 + self.fee_pct)
        sell_price = spread_sell * (1 - self.fee_pct)

        notes = (
            "Estimation Revolut : spread 0,5% + frais 1,5% sur l'achat/vente."
        )

        return BrokerQuote(
            broker=self.name,
            buy_price=buy_price,
            sell_price=sell_price,
            currency="€",
            notes=notes,
            metadata={
                "spread_pct": self.spread_pct,
                "fee_pct": self.fee_pct,
            },
        )
