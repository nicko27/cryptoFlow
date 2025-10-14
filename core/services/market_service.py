"""
Market Service - Gestion des données de marché [FIXED]
"""

import threading
from typing import List, Optional, Dict
from datetime import timedelta
from core.models import (
    MarketData, CryptoPrice, TechnicalIndicators,
    Prediction, PredictionType, OpportunityScore, now_utc
)
from api.binance_api import BinanceAPI
import logging

logger = logging.getLogger("CryptoBot.MarketService")


class MarketService:
    """Service de gestion des données de marché avec thread safety"""
    
    # Constantes
    CACHE_TTL_SECONDS = 60
    MAX_HISTORY_SIZE = 1000
    
    def __init__(self, binance_api: BinanceAPI):
        self.binance_api = binance_api
        self.market_cache: Dict[str, MarketData] = {}
        self.price_history_cache: Dict[str, List[CryptoPrice]] = {}
        
        # Thread safety
        self._cache_lock = threading.RLock()
        self._history_lock = threading.RLock()
    
    def get_market_data(self, symbol: str, refresh: bool = True) -> Optional[MarketData]:
        """
        Récupère les données de marché complètes pour un symbole
        
        Args:
            symbol: Symbole de la crypto
            refresh: Force le rafraîchissement des données
        
        Returns:
            MarketData ou None
        """
        # Cache check avec thread safety
        if not refresh:
            with self._cache_lock:
                if symbol in self.market_cache:
                    cached = self.market_cache[symbol]
                    age = (now_utc() - cached.current_price.timestamp).total_seconds()
                    if age < self.CACHE_TTL_SECONDS:
                        logger.debug(f"Using cached data for {symbol} (age: {age:.1f}s)")
                        return cached
        
        try:
            # Récupération prix actuel
            current_price = self.binance_api.get_current_price(symbol)
            if not current_price:
                logger.warning(f"Could not get current price for {symbol}")
                return None
            
            # Récupération historique depuis API
            price_history = self.binance_api.get_price_history(symbol, interval="1m", limit=200)
            
            # Ajouter au cache d'historique avec thread safety
            with self._history_lock:
                if symbol not in self.price_history_cache:
                    self.price_history_cache[symbol] = []
                
                self.price_history_cache[symbol].append(current_price)
                
                # Garder seulement les MAX_HISTORY_SIZE derniers
                if len(self.price_history_cache[symbol]) > self.MAX_HISTORY_SIZE:
                    self.price_history_cache[symbol] = self.price_history_cache[symbol][-self.MAX_HISTORY_SIZE:]
                
                # Combiner historique API + cache (dédupliqué)
                all_prices = self._deduplicate_prices(price_history + self.price_history_cache[symbol])
            
            # Calculer indicateurs techniques
            technical_indicators = self.binance_api.calculate_technical_indicators(all_prices)
            
            # Récupérer données dérivés
            funding_rate = self.binance_api.get_funding_rate(symbol)
            open_interest = self.binance_api.get_open_interest(symbol)
            fear_greed = self.binance_api.get_fear_greed_index()
            
            # Créer MarketData
            market_data = MarketData(
                symbol=symbol,
                current_price=current_price,
                technical_indicators=technical_indicators,
                funding_rate=funding_rate,
                open_interest=open_interest,
                fear_greed_index=fear_greed,
                price_history=all_prices[-200:]  # Garder les 200 derniers
            )
            
            # Mise à jour cache avec thread safety
            with self._cache_lock:
                self.market_cache[symbol] = market_data
            
            logger.info(f"Updated market data for {symbol}: {current_price.price_eur:.2f}€")
            return market_data
        
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}", exc_info=True)
            return None
    
    def _deduplicate_prices(self, prices: List[CryptoPrice]) -> List[CryptoPrice]:
        """Déduplique les prix par timestamp"""
        seen = {}
        for price in prices:
            ts = int(price.timestamp.timestamp())
            if ts not in seen:
                seen[ts] = price
        
        return sorted(seen.values(), key=lambda p: p.timestamp)
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[CryptoPrice]:
        """
        Récupère l'historique des prix
        
        Args:
            symbol: Symbole de la crypto
            hours: Nombre d'heures d'historique
        
        Returns:
            Liste de CryptoPrice
        """
        with self._history_lock:
            if symbol not in self.price_history_cache:
                # Récupérer depuis l'API
                prices = self.binance_api.get_price_history(symbol, interval="1h", limit=hours)
                self.price_history_cache[symbol] = prices
                return prices
            
            # Filtrer depuis le cache avec timezone aware
            cutoff = now_utc() - timedelta(hours=hours)
            return [p for p in self.price_history_cache[symbol] if p.timestamp >= cutoff]
    
    def calculate_price_change(self, symbol: str, minutes: int) -> float:
        """
        Calcule le changement de prix sur N minutes
        
        Args:
            symbol: Symbole de la crypto
            minutes: Nombre de minutes
        
        Returns:
            Pourcentage de changement
        """
        with self._cache_lock:
            market_data = self.market_cache.get(symbol)
            if not market_data:
                market_data = self.get_market_data(symbol, refresh=False)
                if not market_data:
                    return 0.0
            
            return market_data.get_price_change(minutes)
    
    def get_extremes(self, symbol: str, hours: int = 168) -> Dict[str, float]:
        """
        Trouve les prix min/max/avg sur une période
        
        Args:
            symbol: Symbole de la crypto
            hours: Nombre d'heures (défaut: 7 jours)
        
        Returns:
            Dict avec min, max, avg
        """
        prices = self.get_price_history(symbol, hours)
        
        if not prices:
            logger.warning(f"No price history for {symbol}")
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        
        price_values = [p.price_eur for p in prices]
        
        return {
            "min": min(price_values),
            "max": max(price_values),
            "avg": sum(price_values) / len(price_values)
        }
    
    def predict_price_movement(self, market_data: MarketData) -> Prediction:
        """
        Prédit le mouvement de prix basé sur les indicateurs
        
        Args:
            market_data: Données de marché
        
        Returns:
            Prediction
        """
        ti = market_data.technical_indicators
        trend_score = 0
        signals = []
        
        # Analyse RSI
        if ti.rsi < 30:
            trend_score += 2
            signals.append("RSI survendu (rebond probable)")
        elif ti.rsi < 40:
            trend_score += 1
            signals.append("RSI bas (opportunité)")
        elif ti.rsi > 70:
            trend_score -= 2
            signals.append("RSI suracheté (correction possible)")
        elif ti.rsi > 60:
            trend_score -= 1
            signals.append("RSI élevé (prudence)")
        
        # Analyse MACD
        if ti.macd_histogram > 0:
            trend_score += 1
            signals.append("MACD positif")
        else:
            trend_score -= 1
            signals.append("MACD négatif")
        
        # Moyennes mobiles
        current_price = market_data.current_price.price_eur
        if ti.ma20 > 0:
            if current_price > ti.ma20:
                trend_score += 1
                signals.append("Au-dessus MA20")
            else:
                trend_score -= 1
                signals.append("En-dessous MA20")
        
        # Bollinger Bands
        if ti.bollinger_lower > 0 and current_price < ti.bollinger_lower:
            trend_score += 1
            signals.append("Prix sous bande de Bollinger (survente)")
        elif ti.bollinger_upper > 0 and current_price > ti.bollinger_upper:
            trend_score -= 1
            signals.append("Prix au-dessus bande de Bollinger (surachat)")
        
        # Support/Résistance
        if ti.support > 0:
            distance_to_support = abs(current_price - ti.support) / current_price * 100
            if distance_to_support < 2:
                trend_score += 1
                signals.append("Proche du support")
        
        if ti.resistance > 0:
            distance_to_resistance = abs(ti.resistance - current_price) / current_price * 100
            if distance_to_resistance < 2:
                trend_score -= 1
                signals.append("Proche résistance")
        
        # Déterminer la prédiction
        if trend_score >= 3:
            prediction_type = PredictionType.BULLISH
            direction = "📈"
            confidence = min(85, 60 + trend_score * 5)
            target_high = ti.resistance if ti.resistance > 0 else current_price * 1.05
            target_low = current_price * 0.97
        elif trend_score >= 1:
            prediction_type = PredictionType.SLIGHTLY_BULLISH
            direction = "↗️"
            confidence = 55 + trend_score * 5
            target_high = current_price * 1.03
            target_low = current_price * 0.98
        elif trend_score <= -3:
            prediction_type = PredictionType.BEARISH
            direction = "📉"
            confidence = min(85, 60 - trend_score * 5)
            target_low = ti.support if ti.support > 0 else current_price * 0.95
            target_high = current_price * 1.03
        elif trend_score <= -1:
            prediction_type = PredictionType.SLIGHTLY_BEARISH
            direction = "↘️"
            confidence = 55 - trend_score * 5
            target_low = current_price * 0.97
            target_high = current_price * 1.02
        else:
            prediction_type = PredictionType.NEUTRAL
            direction = "➡️"
            confidence = 50
            target_high = ti.resistance if ti.resistance > 0 else current_price * 1.05
            target_low = ti.support if ti.support > 0 else current_price * 0.95
        
        # Timeline
        if prediction_type in [PredictionType.BULLISH, PredictionType.SLIGHTLY_BULLISH]:
            short_mult = 1.005 if prediction_type == PredictionType.SLIGHTLY_BULLISH else 1.02
            medium_mult = 1.03 if prediction_type == PredictionType.SLIGHTLY_BULLISH else 1.06
            long_mult = 1.05 if prediction_type == PredictionType.SLIGHTLY_BULLISH else 1.10
        elif prediction_type in [PredictionType.BEARISH, PredictionType.SLIGHTLY_BEARISH]:
            short_mult = 0.995 if prediction_type == PredictionType.SLIGHTLY_BEARISH else 0.98
            medium_mult = 0.97 if prediction_type == PredictionType.SLIGHTLY_BEARISH else 0.95
            long_mult = 0.96 if prediction_type == PredictionType.SLIGHTLY_BEARISH else 0.92
        else:
            short_mult = 1.0
            medium_mult = 1.0
            long_mult = 1.0
        
        logger.debug(f"Prediction for {market_data.symbol}: {prediction_type.value} "
                    f"(score: {trend_score}, confidence: {confidence}%)")
        
        return Prediction(
            prediction_type=prediction_type,
            confidence=confidence,
            direction=direction,
            trend_score=trend_score,
            signals=signals,
            target_high=target_high,
            target_low=target_low,
            timeframe_short=current_price * short_mult,
            timeframe_medium=current_price * medium_mult,
            timeframe_long=current_price * long_mult
        )
    
    def calculate_opportunity_score(self, market_data: MarketData, prediction: Prediction) -> OpportunityScore:
        """
        Calcule le score d'opportunité d'achat (0-10)
        
        Args:
            market_data: Données de marché
            prediction: Prédiction
        
        Returns:
            OpportunityScore
        """
        score = 5.0
        reasons = []
        
        # Prédiction
        if prediction.prediction_type == PredictionType.BULLISH:
            if prediction.confidence >= 75:
                score += 2
                reasons.append("✅ Signal très haussier")
            else:
                score += 1
                reasons.append("✅ Signal haussier")
        elif prediction.prediction_type == PredictionType.SLIGHTLY_BULLISH:
            score += 0.5
            reasons.append("✅ Tendance légèrement positive")
        elif prediction.prediction_type == PredictionType.BEARISH:
            score -= 2
            reasons.append("⚠️ Signal baissier")
        elif prediction.prediction_type == PredictionType.SLIGHTLY_BEARISH:
            score -= 1
            reasons.append("⚠️ Tendance légèrement négative")
        
        # RSI
        rsi = market_data.technical_indicators.rsi
        if rsi < 30:
            score += 2
            reasons.append("✅ Prix très bas (survendu)")
        elif rsi < 40:
            score += 1
            reasons.append("✅ Prix assez bas")
        elif rsi > 70:
            score -= 1.5
            reasons.append("⚠️ Prix très haut (suracheté)")
        
        # Fear & Greed
        if market_data.fear_greed_index:
            fgi = market_data.fear_greed_index
            if fgi <= 25:
                score += 2
                reasons.append("✅ Marché en peur extrême")
            elif fgi <= 40:
                score += 1
                reasons.append("✅ Marché craintif")
            elif fgi >= 75:
                score -= 1.5
                reasons.append("⚠️ Marché très euphorique")
        
        # Changement 24h
        change_24h = market_data.current_price.change_24h
        if change_24h < -10:
            score += 1.5
            reasons.append(f"✅ Forte baisse récente ({change_24h:.1f}%)")
        elif change_24h < -5:
            score += 0.5
            reasons.append("✅ Baisse récente")
        elif change_24h > 15:
            score -= 1
            reasons.append("⚠️ Forte hausse récente")
        
        # Position vs historique
        try:
            extremes = self.get_extremes(market_data.symbol, hours=168)
            if extremes["min"] > 0:
                current = market_data.current_price.price_eur
                distance_to_min = ((current - extremes["min"]) / extremes["min"]) * 100
                distance_to_max = ((extremes["max"] - current) / extremes["max"]) * 100
                
                if distance_to_min < 10:
                    score += 1.5
                    reasons.append("✅ Proche du plus bas récent")
                elif distance_to_max < 10:
                    score -= 1
                    reasons.append("⚠️ Proche du plus haut récent")
        except Exception as e:
            logger.warning(f"Could not calculate extremes: {e}")
        
        # Borner le score
        score = max(0, min(10, int(score)))
        
        # Recommandation
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
        
        logger.info(f"Opportunity score for {market_data.symbol}: {score}/10")
        
        return OpportunityScore(
            score=score,
            reasons=reasons[:5],  # Max 5 raisons
            recommendation=recommendation
        )
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Vide le cache"""
        with self._cache_lock, self._history_lock:
            if symbol:
                self.market_cache.pop(symbol, None)
                self.price_history_cache.pop(symbol, None)
                logger.info(f"Cleared cache for {symbol}")
            else:
                self.market_cache.clear()
                self.price_history_cache.clear()
                logger.info("Cleared all cache")
