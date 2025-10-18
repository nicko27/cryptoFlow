"""
Courtier Binance - utilise le prix courant et un spread de frais estimé.
"""

from typing import Optional

from brokers.base import Broker
from core.models import MarketData, BrokerQuote


class BinanceBroker(Broker):
    name = "Binance"
    slug = "binance"
    fee_pct = 0.001  # 0,1%

    def configure(self, settings: dict) -> None:
        if not settings:
            return
        fee = settings.get("fee_pct")
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

        buy_price = price * (1 + self.fee_pct)
        sell_price = price * (1 - self.fee_pct)

        return BrokerQuote(
            broker=self.name,
            buy_price=buy_price,
            sell_price=sell_price,
            currency="€",
            notes="Inclut les frais maker/taker Binance estimés à 0,1%.",
            metadata={"fee_pct": self.fee_pct},
        )
