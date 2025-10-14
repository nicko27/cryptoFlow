"""Market Service - Gestion des données de marché [TIMEZONE FIXED]"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from core.models import MarketData, CryptoPrice, TechnicalIndicators, Prediction, PredictionType, OpportunityScore
from api.binance_api import BinanceAPI

class MarketService:
    def __init__(self, binance_api: BinanceAPI):
        self.binance_api = binance_api
        self.market_cache: Dict[str, MarketData] = {}
        self.price_history_cache: Dict[str, List[CryptoPrice]] = {}
    
    def get_market_data(self, symbol: str, refresh: bool = True) -> Optional[MarketData]:
        if not refresh and symbol in self.market_cache:
            cached = self.market_cache[symbol]
            age = (datetime.now(timezone.utc) - cached.current_price.timestamp).total_seconds()
            if age < 60:
                return cached
        
        current_price = self.binance_api.get_current_price(symbol)
        if not current_price:
            return None
        
        price_history = self.binance_api.get_price_history(symbol, interval="1m", limit=200)
        if symbol not in self.price_history_cache:
            self.price_history_cache[symbol] = []
        
        self.price_history_cache[symbol].append(current_price)
        self.price_history_cache[symbol] = self.price_history_cache[symbol][-1000:]
        all_prices = price_history + self.price_history_cache[symbol]
        technical_indicators = self.binance_api.calculate_technical_indicators(all_prices)
        
        market_data = MarketData(
            symbol=symbol,
            current_price=current_price,
            technical_indicators=technical_indicators,
            funding_rate=self.binance_api.get_funding_rate(symbol),
            open_interest=self.binance_api.get_open_interest(symbol),
            fear_greed_index=self.binance_api.get_fear_greed_index(),
            price_history=all_prices[-200:]
        )
        
        self.market_cache[symbol] = market_data
        return market_data
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[CryptoPrice]:
        if symbol not in self.price_history_cache:
            prices = self.binance_api.get_price_history(symbol, interval="1h", limit=hours)
            self.price_history_cache[symbol] = prices
            return prices
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [p for p in self.price_history_cache[symbol] if p.timestamp >= cutoff]
    
    def get_extremes(self, symbol: str, hours: int = 168) -> Dict[str, float]:
        prices = self.get_price_history(symbol, hours)
        if not prices:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        price_values = [p.price_eur for p in prices]
        return {"min": min(price_values), "max": max(price_values), "avg": sum(price_values) / len(price_values)}
    
    def predict_price_movement(self, market_data: MarketData) -> Prediction:
        ti = market_data.technical_indicators
        trend_score = 0
        signals = []
        
        if ti.rsi < 30:
            trend_score += 2
            signals.append("RSI survendu (rebond probable)")
        elif ti.rsi < 40:
            trend_score += 1
            signals.append("RSI bas (opportunité)")
        elif ti.rsi > 70:
            trend_score -= 2
            signals.append("RSI suracheté (correction possible)")
        
        if ti.macd_histogram > 0:
            trend_score += 1
            signals.append("MACD positif")
        else:
            trend_score -= 1
            signals.append("MACD négatif")
        
        current_price = market_data.current_price.price_eur
        if current_price > ti.ma20:
            trend_score += 1
            signals.append("Au-dessus MA20")
        
        if trend_score >= 3:
            prediction_type = PredictionType.BULLISH
            direction = "📈"
            confidence = min(85, 60 + trend_score * 5)
        elif trend_score >= 1:
            prediction_type = PredictionType.SLIGHTLY_BULLISH
            direction = "↗️"
            confidence = 55 + trend_score * 5
        elif trend_score <= -3:
            prediction_type = PredictionType.BEARISH
            direction = "📉"
            confidence = min(85, 60 - trend_score * 5)
        elif trend_score <= -1:
            prediction_type = PredictionType.SLIGHTLY_BEARISH
            direction = "↘️"
            confidence = 55 - trend_score * 5
        else:
            prediction_type = PredictionType.NEUTRAL
            direction = "➡️"
            confidence = 50
        
        return Prediction(
            prediction_type=prediction_type,
            confidence=confidence,
            direction=direction,
            trend_score=trend_score,
            signals=signals,
            target_high=current_price * 1.05,
            target_low=current_price * 0.95,
            timeframe_short=current_price * 1.02,
            timeframe_medium=current_price * 1.04,
            timeframe_long=current_price * 1.06
        )
    
    def calculate_opportunity_score(self, market_data: MarketData, prediction: Prediction) -> OpportunityScore:
        score = 5.0
        reasons = []
        
        if prediction.prediction_type == PredictionType.BULLISH:
            if prediction.confidence >= 75:
                score += 2
                reasons.append("✅ Signal très haussier")
            else:
                score += 1
                reasons.append("✅ Signal haussier")
        elif prediction.prediction_type == PredictionType.BEARISH:
            score -= 2
            reasons.append("⚠️ Signal baissier")
        
        rsi = market_data.technical_indicators.rsi
        if rsi < 30:
            score += 2
            reasons.append("✅ Prix très bas (survendu)")
        elif rsi > 70:
            score -= 1.5
            reasons.append("⚠️ Prix très haut (suracheté)")
        
        if market_data.fear_greed_index:
            fgi = market_data.fear_greed_index
            if fgi <= 25:
                score += 2
                reasons.append("✅ Marché en peur extrême")
        
        score = max(0, min(10, int(score)))
        
        if score >= 8:
            recommendation = "EXCELLENTE opportunité d'achat ! 🎯"
        elif score >= 7:
            recommendation = "Très bonne opportunité 💎"
        elif score >= 6:
            recommendation = "Opportunité correcte"
        elif score >= 4:
            recommendation = "Moment neutre ⚖️"
        else:
            recommendation = "Pas un bon moment ❌"
        
        return OpportunityScore(score=score, reasons=reasons[:5], recommendation=recommendation)
