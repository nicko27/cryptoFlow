"""API Binance [FIXED]"""
import requests
from typing import List, Optional
from datetime import datetime, timezone
from core.models import CryptoPrice, TechnicalIndicators

class BinanceAPI:
    BASE_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"
    
    def __init__(self, timeout: int = 10, revolut_api=None):
        self.timeout = timeout
        self.session = requests.Session()
        self.revolut_api = revolut_api
    
    def get_current_price(self, symbol: str) -> Optional[CryptoPrice]:
        try:
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            params = {"symbol": f"{symbol}USDT"}
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            usd_to_eur = self._get_usd_to_eur()
            return CryptoPrice(
                symbol=symbol,
                price_usd=float(data["lastPrice"]),
                price_eur=float(data["lastPrice"]) * usd_to_eur,
                timestamp=datetime.now(timezone.utc),
                volume_24h=float(data["volume"]),
                change_24h=float(data["priceChangePercent"]),
                high_24h=float(data["highPrice"]) * usd_to_eur,
                low_24h=float(data["lowPrice"]) * usd_to_eur
            )
        except:
            return None
    
    def get_price_history(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[CryptoPrice]:
        try:
            url = f"{self.BASE_URL}/api/v3/klines"
            params = {"symbol": f"{symbol}USDT", "interval": interval, "limit": min(limit, 1000)}
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            usd_to_eur = self._get_usd_to_eur()
            prices = []
            for candle in data:
                timestamp = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)
                prices.append(CryptoPrice(
                    symbol=symbol,
                    price_usd=float(candle[4]),
                    price_eur=float(candle[4]) * usd_to_eur,
                    timestamp=timestamp,
                    volume_24h=float(candle[5])
                ))
            return prices
        except:
            return []
    
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 1}
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return float(data[-1]["fundingRate"]) * 100.0 if data else None
        except:
            return None
    
    def get_open_interest(self, symbol: str) -> Optional[float]:
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/openInterest"
            params = {"symbol": f"{symbol}USDT"}
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return float(response.json().get("openInterest", 0))
        except:
            return None
    
    def _get_usd_to_eur(self) -> float:
        if not hasattr(self, '_usd_eur_cache'):
            self._usd_eur_cache = {"rate": 0.92, "timestamp": 0}
        now = datetime.now(timezone.utc).timestamp()
        cache_age = now - self._usd_eur_cache["timestamp"]
        if cache_age < 3600:
            return self._usd_eur_cache["rate"]
        for api_url in ["https://api.exchangerate-api.com/v4/latest/USD"]:
            try:
                response = self.session.get(api_url, timeout=5)
                response.raise_for_status()
                rate = response.json().get("rates", {}).get("EUR")
                if rate:
                    self._usd_eur_cache = {"rate": float(rate), "timestamp": now}
                    return float(rate)
            except:
                pass
        return 0.92
    
    def get_fear_greed_index(self) -> Optional[int]:
        try:
            response = self.session.get("https://api.alternative.me/fng/", params={"limit": 1}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return int(data["data"][0]["value"]) if "data" in data and data["data"] else None
        except:
            return None
    
    def calculate_technical_indicators(self, prices: List[CryptoPrice]) -> TechnicalIndicators:
        if not prices or len(prices) < 14:
            return TechnicalIndicators()
        closes = [p.price_eur for p in prices]
        return TechnicalIndicators(
            rsi=self._calculate_rsi(closes),
            ma20=sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 20 else closes[-1],
            ma50=sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else closes[-1]
        )
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
