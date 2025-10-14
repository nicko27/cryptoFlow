"""
API Client pour Binance
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from core.models import CryptoPrice, TechnicalIndicators


class BinanceAPI:
    """Client API Binance"""
    
    BASE_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_current_price(self, symbol: str) -> Optional[CryptoPrice]:
        """Récupère le prix actuel"""
        try:
            # Prix spot
            url = f"{self.BASE_URL}/api/v3/ticker/24hr"
            params = {"symbol": f"{symbol}USDT"}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Taux de change USD -> EUR
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
        
        except Exception as e:
            print(f"Erreur récupération prix {symbol}: {e}")
            return None
    
    def get_price_history(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[CryptoPrice]:
        """Récupère l'historique des prix"""
        try:
            url = f"{self.BASE_URL}/api/v3/klines"
            params = {
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            usd_to_eur = self._get_usd_to_eur()
            
            prices = []
            for candle in data:
                timestamp = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)
                close_price = float(candle[4])
                
                prices.append(CryptoPrice(
                    symbol=symbol,
                    price_usd=close_price,
                    price_eur=close_price * usd_to_eur,
                    timestamp=timestamp,
                    volume_24h=float(candle[5])
                ))
            
            return prices
        
        except Exception as e:
            print(f"Erreur récupération historique {symbol}: {e}")
            return []
    
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Récupère le funding rate"""
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 1}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data:
                return float(data[-1]["fundingRate"]) * 100.0
            
            return None
        
        except Exception:
            return None
    
    def get_open_interest(self, symbol: str) -> Optional[float]:
        """Récupère l'Open Interest"""
        try:
            url = f"{self.FUTURES_URL}/fapi/v1/openInterest"
            params = {"symbol": f"{symbol}USDT"}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            return float(data.get("openInterest", 0))
        
        except Exception:
            return None
    
    def _get_usd_to_eur(self, use_cache: bool = True) -> float:
        """Récupère le taux de change USD->EUR"""
        # Cache simple (1h)
        if not hasattr(self, '_usd_eur_cache'):
            self._usd_eur_cache = {"rate": 0.92, "timestamp": 0}
        
        now = datetime.now().timestamp()
        cache_age = now - self._usd_eur_cache["timestamp"]
        
        if use_cache and cache_age < 3600:
            return self._usd_eur_cache["rate"]
        
        # Essayer de récupérer le taux réel
        apis = [
            "https://api.exchangerate-api.com/v4/latest/USD",
            "https://open.er-api.com/v6/latest/USD"
        ]
        
        for api_url in apis:
            try:
                response = self.session.get(api_url, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                rate = data.get("rates", {}).get("EUR")
                if rate:
                    self._usd_eur_cache = {"rate": float(rate), "timestamp": now}
                    return float(rate)
            
            except Exception:
                continue
        
        # Retourner le cache si échec
        return self._usd_eur_cache["rate"]
    
    def get_fear_greed_index(self) -> Optional[int]:
        """Récupère le Fear & Greed Index"""
        try:
            url = "https://api.alternative.me/fng/"
            params = {"limit": 1, "format": "json"}
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and data["data"]:
                return int(data["data"][0]["value"])
            
            return None
        
        except Exception:
            return None
    
    def calculate_technical_indicators(self, prices: List[CryptoPrice]) -> TechnicalIndicators:
        """Calcule les indicateurs techniques"""
        if not prices or len(prices) < 14:
            return TechnicalIndicators()
        
        closes = [p.price_eur for p in prices]
        highs = [p.high_24h for p in prices]
        lows = [p.low_24h for p in prices]
        
        return TechnicalIndicators(
            rsi=self._calculate_rsi(closes),
            macd=self._calculate_macd(closes)["macd"],
            macd_signal=self._calculate_macd(closes)["signal"],
            macd_histogram=self._calculate_macd(closes)["histogram"],
            ma20=sum(closes[-20:]) / min(20, len(closes)),
            ma50=sum(closes[-50:]) / min(50, len(closes)),
            ma200=sum(closes[-200:]) / min(200, len(closes)) if len(closes) >= 200 else closes[-1],
            support=self._find_support(lows),
            resistance=self._find_resistance(highs)
        )
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcule le RSI"""
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
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calcule le MACD"""
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        ema12 = prices[-1]  # Simplifié
        ema26 = sum(prices[-26:]) / 26
        
        macd_line = ema12 - ema26
        signal_line = macd_line * 0.9  # Simplifié
        histogram = macd_line - signal_line
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def _find_support(self, lows: List[float]) -> float:
        """Trouve le niveau de support"""
        if not lows:
            return 0.0
        
        recent_lows = sorted(lows[-50:])
        return recent_lows[int(len(recent_lows) * 0.1)]
    
    def _find_resistance(self, highs: List[float]) -> float:
        """Trouve le niveau de résistance"""
        if not highs:
            return 0.0
        
        recent_highs = sorted(highs[-50:])
        return recent_highs[int(len(recent_highs) * 0.9)]
