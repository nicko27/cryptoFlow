"""
Alert Service - Gestion des alertes
"""

from typing import List, Optional, Callable, Dict
from datetime import datetime
from core.models import (
    Alert, AlertType, AlertLevel, MarketData, Prediction,
    PriceLevel, BotConfiguration
)


class AlertService:
    """Service de gestion des alertes"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.price_levels: Dict[str, List[PriceLevel]] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        self._init_price_levels()
    
    def _init_price_levels(self):
        """Initialise les niveaux de prix"""
        for symbol, levels in self.config.price_levels.items():
            if symbol not in self.price_levels:
                self.price_levels[symbol] = []
            
            if "low" in levels:
                self.price_levels[symbol].append(PriceLevel(
                    symbol=symbol,
                    level=levels["low"],
                    level_type="low",
                    buffer=self.config.level_buffer_eur,
                    cooldown_minutes=self.config.level_cooldown_minutes
                ))
            
            if "high" in levels:
                self.price_levels[symbol].append(PriceLevel(
                    symbol=symbol,
                    level=levels["high"],
                    level_type="high",
                    buffer=self.config.level_buffer_eur,
                    cooldown_minutes=self.config.level_cooldown_minutes
                ))
    
    def register_callback(self, callback: Callable[[Alert], None]):
        """Enregistre un callback pour les nouvelles alertes"""
        self.alert_callbacks.append(callback)
    
    def _trigger_callbacks(self, alert: Alert):
        """Déclenche tous les callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Erreur callback alerte: {e}")
    
    def check_alerts(self, market_data: MarketData, prediction: Optional[Prediction] = None) -> List[Alert]:
        """Vérifie toutes les conditions d'alerte"""
        alerts = []
        
        if self.config.enable_alerts:
            price_alerts = self._check_price_alerts(market_data)
            alerts.extend(price_alerts)
        
        if self.config.enable_price_levels:
            level_alerts = self._check_price_levels(market_data)
            alerts.extend(level_alerts)
        
        funding_alerts = self._check_funding_rate(market_data)
        alerts.extend(funding_alerts)
        
        oi_alerts = self._check_open_interest(market_data)
        alerts.extend(oi_alerts)
        
        fgi_alerts = self._check_fear_greed(market_data)
        alerts.extend(fgi_alerts)
        
        if prediction and self.config.enable_predictions:
            pred_alerts = self._check_prediction(market_data, prediction)
            alerts.extend(pred_alerts)
        
        for alert in alerts:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            self._trigger_callbacks(alert)
        
        self.alert_history = self.alert_history[-1000:]
        
        return alerts
    
    def _check_price_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes de changement de prix"""
        alerts = []
        
        change = market_data.get_price_change(self.config.price_lookback_minutes)
        
        if change <= -abs(self.config.price_drop_threshold):
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.PRICE_DROP,
                alert_level=AlertLevel.IMPORTANT,
                message=f"Chute rapide de {change:.2f}% en {self.config.price_lookback_minutes} min",
                metadata={
                    "change_pct": change,
                    "lookback_minutes": self.config.price_lookback_minutes,
                    "current_price": market_data.current_price.price_eur
                }
            )
            alerts.append(alert)
        
        if change >= abs(self.config.price_spike_threshold):
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.PRICE_SPIKE,
                alert_level=AlertLevel.IMPORTANT,
                message=f"Hausse rapide de {change:.2f}% en {self.config.price_lookback_minutes} min",
                metadata={
                    "change_pct": change,
                    "lookback_minutes": self.config.price_lookback_minutes,
                    "current_price": market_data.current_price.price_eur
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_price_levels(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les franchissements de niveaux"""
        alerts = []
        
        symbol = market_data.symbol
        if symbol not in self.price_levels:
            return alerts
        
        current_price = market_data.current_price.price_eur
        
        for price_level in self.price_levels[symbol]:
            if not price_level.can_trigger():
                continue
            
            if price_level.level_type == "low":
                if current_price < (price_level.level - price_level.buffer):
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.CRITICAL,
                        message=f"🚨 {symbol} a cassé le niveau {price_level.level}€ ! (maintenant {current_price:.2f}€)",
                        metadata={
                            "level": price_level.level,
                            "level_type": "low",
                            "current_price": current_price,
                            "buffer": price_level.buffer
                        }
                    )
                    alerts.append(alert)
                    price_level.record_trigger()
                
                elif abs(current_price - price_level.level) < price_level.buffer:
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.WARNING,
                        message=f"⚠️ {symbol} approche du niveau {price_level.level}€ (actuellement {current_price:.2f}€)",
                        metadata={
                            "level": price_level.level,
                            "level_type": "low",
                            "current_price": current_price,
                            "approaching": True
                        }
                    )
                    alerts.append(alert)
                    price_level.record_trigger()
            
            elif price_level.level_type == "high":
                if current_price > (price_level.level + price_level.buffer):
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.CRITICAL,
                        message=f"🚨 {symbol} a dépassé le niveau {price_level.level}€ ! (maintenant {current_price:.2f}€)",
                        metadata={
                            "level": price_level.level,
                            "level_type": "high",
                            "current_price": current_price,
                            "buffer": price_level.buffer
                        }
                    )
                    alerts.append(alert)
                    price_level.record_trigger()
                
                elif abs(current_price - price_level.level) < price_level.buffer:
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.WARNING,
                        message=f"⚠️ {symbol} approche du niveau {price_level.level}€ (actuellement {current_price:.2f}€)",
                        metadata={
                            "level": price_level.level,
                            "level_type": "high",
                            "current_price": current_price,
                            "approaching": True
                        }
                    )
                    alerts.append(alert)
                    price_level.record_trigger()
        
        return alerts
    
    def _check_funding_rate(self, market_data: MarketData) -> List[Alert]:
        """Vérifie le funding rate"""
        alerts = []
        
        if market_data.funding_rate is None:
            return alerts
        
        if market_data.funding_rate <= self.config.funding_negative_threshold:
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.FUNDING_NEGATIVE,
                alert_level=AlertLevel.INFO,
                message=f"Funding négatif : {market_data.funding_rate:.4f}%",
                metadata={"funding_rate": market_data.funding_rate}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_open_interest(self, market_data: MarketData) -> List[Alert]:
        """Vérifie l'Open Interest"""
        return []
    
    def _check_fear_greed(self, market_data: MarketData) -> List[Alert]:
        """Vérifie le Fear & Greed Index"""
        alerts = []
        
        if market_data.fear_greed_index is None:
            return alerts
        
        if market_data.fear_greed_index <= self.config.fear_greed_max:
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.INFO,
                message=f"Peur extrême : {market_data.fear_greed_index}/100",
                metadata={"fgi": market_data.fear_greed_index}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_prediction(self, market_data: MarketData, prediction: Prediction) -> List[Alert]:
        """Vérifie les prédictions"""
        alerts = []
        
        if prediction.confidence >= 70:
            if "HAUSSIER" in prediction.prediction_type.value:
                alert = Alert(
                    alert_id="",
                    symbol=market_data.symbol,
                    alert_type=AlertType.PREDICTION,
                    alert_level=AlertLevel.INFO,
                    message=f"Signal haussier fort ({prediction.confidence}%)",
                    metadata={
                        "prediction": prediction.prediction_type.value,
                        "confidence": prediction.confidence
                    }
                )
                alerts.append(alert)
            
            elif "BAISSIER" in prediction.prediction_type.value:
                alert = Alert(
                    alert_id="",
                    symbol=market_data.symbol,
                    alert_type=AlertType.PREDICTION,
                    alert_level=AlertLevel.WARNING,
                    message=f"Signal baissier fort ({prediction.confidence}%)",
                    metadata={
                        "prediction": prediction.prediction_type.value,
                        "confidence": prediction.confidence
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def get_active_alerts(self, symbol: Optional[str] = None) -> List[Alert]:
        """Récupère les alertes actives"""
        if symbol:
            return [a for a in self.active_alerts if a.symbol == symbol]
        return self.active_alerts
    
    def acknowledge_alert(self, alert_id: str):
        """Marque une alerte comme acquittée"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self.active_alerts.remove(alert)
                break
    
    def clear_active_alerts(self, symbol: Optional[str] = None):
        """Efface les alertes actives"""
        if symbol:
            self.active_alerts = [a for a in self.active_alerts if a.symbol != symbol]
        else:
            self.active_alerts.clear()
