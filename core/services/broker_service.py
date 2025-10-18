"""
Service d'agrégation des courtiers.
"""

from typing import List, Optional, Type

from brokers import Broker, discover_brokers
from core.models import BotConfiguration, MarketData, BrokerQuote


class BrokerService:
    """Collecte les cotations auprès des courtiers disponibles."""

    def __init__(
        self,
        config: Optional[BotConfiguration] = None,
        brokers: Optional[List[Broker]] = None,
    ):
        initial_brokers = brokers or discover_brokers()
        self._broker_classes: List[Type[Broker]] = [broker.__class__ for broker in initial_brokers]
        self._brokers: List[Broker] = []
        self.configure(config)

    def configure(self, config: Optional[BotConfiguration]) -> None:
        self._config = config
        enabled_slugs = None
        if config and config.enabled_brokers:
            enabled_slugs = {slug.lower() for slug in config.enabled_brokers}

        broker_settings = config.broker_settings if config else {}

        self._brokers = []
        for cls in self._broker_classes:
            broker = cls()
            if enabled_slugs is not None and broker.slug.lower() not in enabled_slugs:
                continue
            settings = broker_settings.get(broker.slug, {})
            if settings:
                broker.configure(settings)
            self._brokers.append(broker)

    def get_quotes(self, symbol: str, market_data: MarketData) -> List[BrokerQuote]:
        quotes: List[BrokerQuote] = []
        for broker in self._brokers:
            if not broker.supports(symbol):
                continue
            try:
                quote = broker.get_quote(symbol, market_data)
            except Exception as exc:  # pragma: no cover - log/ignore
                quote = None
            if quote:
                quotes.append(quote)
        quotes.sort(key=lambda q: q.broker)
        return quotes
