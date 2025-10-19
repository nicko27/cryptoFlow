"""
Alert Service - Génération et gestion des alertes
FIXED: Problème 4 - Import Dict ajouté
"""

from typing import List, Optional, Callable, Dict  # FIXED: Problème 4 - Dict ajouté
from datetime import datetime, timezone

from core.models import (
    Alert, AlertType, AlertLevel, MarketData, Prediction,
    BotConfiguration, PredictionType
)


class AlertService:
    """Service de gestion des alertes"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.callbacks: List[Callable[[Alert], None]] = []
        self.alert_history: List[Alert] = []
        self.price_levels_triggered: Dict[str, datetime] = {}  # FIXED: Dict utilisé
    
    def register_callback(self, callback: Callable[[Alert], None]):
        """Enregistre un callback pour les alertes"""
        self.callbacks.append(callback)
    
    def check_alerts(
        self,
        market_data: MarketData,
        prediction: Optional[Prediction] = None
    ) -> List[Alert]:
        """
        Vérifie toutes les conditions d'alerte
        
        Args:
            market_data: Données du marché
            prediction: Prédiction optionnelle
        
        Returns:
            Liste des alertes générées
        """
        alerts = []
        
        # Alertes de prix
        alerts.extend(self._check_price_alerts(market_data))
        
        # Alertes RSI
        alerts.extend(self._check_rsi_alerts(market_data))
        
        # Alertes Fear & Greed
        alerts.extend(self._check_fear_greed_alerts(market_data))
        
        # Alertes de niveaux
        if self.config.enable_price_levels:
            alerts.extend(self._check_price_levels(market_data))
        
        # Alertes de prédiction
        if prediction and self.config.enable_predictions:
            alerts.extend(self._check_prediction_alerts(market_data, prediction))
        
        # Alertes de funding rate
        if market_data.funding_rate is not None:
            alerts.extend(self._check_funding_alerts(market_data))
        
        # Alertes Open Interest
        if market_data.open_interest_change is not None:
            alerts.extend(self._check_open_interest_alerts(market_data))
        
        # Sauvegarder et notifier
        for alert in alerts:
            self.alert_history.append(alert)
            self._notify_callbacks(alert)
        
        return alerts
    
    def _check_price_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes de changement de prix"""
        alerts = []
        
        # Calcul du changement de prix
        change = market_data.get_price_change(self.config.price_lookback_minutes)
        
        if change is None:
            return alerts
        
        # Baisse importante
        if change <= -self.config.price_drop_threshold:
            alerts.append(Alert(
                alert_type=AlertType.PRICE_DROP,
                alert_level=AlertLevel.IMPORTANT if change <= -10 else AlertLevel.WARNING,
                symbol=market_data.symbol,
                message=f"Chute de {abs(change):.1f}% en {self.config.price_lookback_minutes}min",
                price=market_data.current_price.price_eur,
                metadata={"change_pct": change, "timeframe_minutes": self.config.price_lookback_minutes}
            ))
        
        # Hausse importante
        elif change >= self.config.price_spike_threshold:
            alerts.append(Alert(
                alert_type=AlertType.PRICE_SPIKE,
                alert_level=AlertLevel.IMPORTANT if change >= 10 else AlertLevel.INFO,
                symbol=market_data.symbol,
                message=f"Hausse de {change:.1f}% en {self.config.price_lookback_minutes}min",
                price=market_data.current_price.price_eur,
                metadata={"change_pct": change, "timeframe_minutes": self.config.price_lookback_minutes}
            ))
        
        return alerts
    
    def _check_rsi_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes RSI"""
        alerts = []
        rsi = market_data.technical_indicators.rsi
        
        # Survente
        if rsi <= self.config.rsi_oversold:
            alerts.append(Alert(
                alert_type=AlertType.OPPORTUNITY,
                alert_level=AlertLevel.IMPORTANT,
                symbol=market_data.symbol,
                message=f"RSI en survente ({rsi:.0f})",
                price=market_data.current_price.price_eur,
                metadata={"rsi": rsi, "threshold": self.config.rsi_oversold}
            ))
        
        # Surachat
        elif rsi >= self.config.rsi_overbought:
            alerts.append(Alert(
                alert_type=AlertType.OPPORTUNITY,
                alert_level=AlertLevel.WARNING,
                symbol=market_data.symbol,
                message=f"RSI en surachat ({rsi:.0f})",
                price=market_data.current_price.price_eur,
                metadata={"rsi": rsi, "threshold": self.config.rsi_overbought}
            ))
        
        return alerts
    
    def _check_fear_greed_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes Fear & Greed Index"""
        alerts = []
        
        if market_data.fear_greed_index is None:
            return alerts
        
        fg = market_data.fear_greed_index
        
        # Peur extrême
        if fg <= self.config.fear_greed_extreme_fear:
            alerts.append(Alert(
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.IMPORTANT,
                symbol=market_data.symbol,
                message=f"Peur extrême : {fg}/100",
                price=market_data.current_price.price_eur,
                metadata={"fear_greed_index": fg, "sentiment": "extreme_fear"}
            ))
        
        # Avidité extrême
        elif fg >= self.config.fear_greed_extreme_greed:
            alerts.append(Alert(
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.WARNING,
                symbol=market_data.symbol,
                message=f"Avidité extrême : {fg}/100",
                price=market_data.current_price.price_eur,
                metadata={"fear_greed_index": fg, "sentiment": "extreme_greed"}
            ))
        
        # Peur simple (30-40)
        elif 30 <= fg <= 40:
            alerts.append(Alert(
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.INFO,
                symbol=market_data.symbol,
                message=f"Peur sur le marché : {fg}/100",
                price=market_data.current_price.price_eur,
                metadata={"fear_greed_index": fg, "sentiment": "fear"}
            ))
        
        # Avidité simple (60-70)
        elif 60 <= fg <= 70:
            alerts.append(Alert(
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.INFO,
                symbol=market_data.symbol,
                message=f"Avidité sur le marché : {fg}/100",
                price=market_data.current_price.price_eur,
                metadata={"fear_greed_index": fg, "sentiment": "greed"}
            ))
        
        return alerts
    
    def _check_price_levels(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les niveaux de prix configurés"""
        alerts = []
        symbol = market_data.symbol
        current_price = market_data.current_price.price_eur
        
        if symbol not in self.config.price_levels:
            return alerts
        
        levels = self.config.price_levels[symbol]
        
        # Niveau bas
        if "low" in levels:
            low_level = levels["low"]
            buffer = levels.get("buffer", 2.0)
            
            if current_price <= low_level * (1 + buffer / 100):
                # Vérifier cooldown
                key = f"{symbol}_low"
                if self._can_trigger_level(key):
                    alerts.append(Alert(
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.CRITICAL,
                        symbol=symbol,
                        message=f"Prix proche du niveau bas ({low_level:.2f}€)",
                        price=current_price,
                        metadata={"level": low_level, "level_type": "low"}
                    ))
                    self.price_levels_triggered[key] = datetime.now(timezone.utc)
        
        # Niveau haut
        if "high" in levels:
            high_level = levels["high"]
            buffer = levels.get("buffer", 2.0)
            
            if current_price >= high_level * (1 - buffer / 100):
                # Vérifier cooldown
                key = f"{symbol}_high"
                if self._can_trigger_level(key):
                    alerts.append(Alert(
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.IMPORTANT,
                        symbol=symbol,
                        message=f"Prix proche du niveau haut ({high_level:.2f}€)",
                        price=current_price,
                        metadata={"level": high_level, "level_type": "high"}
                    ))
                    self.price_levels_triggered[key] = datetime.now(timezone.utc)
        
        return alerts
    
    def _can_trigger_level(self, key: str, cooldown_minutes: int = 30) -> bool:
        """Vérifie si un niveau peut être déclenché (cooldown)"""
        if key not in self.price_levels_triggered:
            return True
        
        last_triggered = self.price_levels_triggered[key]
        elapsed = (datetime.now(timezone.utc) - last_triggered).total_seconds() / 60
        
        return elapsed >= cooldown_minutes
    
    def _check_prediction_alerts(
        self,
        market_data: MarketData,
        prediction: Prediction
    ) -> List[Alert]:
        """Vérifie les alertes basées sur les prédictions"""
        alerts = []
        
        # Prédiction très confiante
        if prediction.confidence >= 80:
            level = AlertLevel.IMPORTANT if prediction.confidence >= 90 else AlertLevel.INFO
            
            alerts.append(Alert(
                alert_type=AlertType.PREDICTION,
                alert_level=level,
                symbol=market_data.symbol,
                message=f"Prédiction forte : {prediction.prediction_type.value} ({prediction.confidence}%)",
                price=market_data.current_price.price_eur,
                metadata={
                    "prediction_type": prediction.prediction_type.value,
                    "confidence": prediction.confidence,
                    "direction": prediction.direction
                }
            ))
        
        return alerts
    
    def _check_funding_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes de funding rate"""
        alerts = []
        
        if market_data.funding_rate is None:
            return alerts
        
        # Funding négatif important
        if market_data.funding_rate < -0.01:  # -1%
            alerts.append(Alert(
                alert_type=AlertType.FUNDING_NEGATIVE,
                alert_level=AlertLevel.WARNING,
                symbol=market_data.symbol,
                message=f"Funding négatif : {market_data.funding_rate * 100:.2f}%",
                price=market_data.current_price.price_eur,
                metadata={"funding_rate": market_data.funding_rate}
            ))
        
        return alerts
    
    def _check_open_interest_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes de changement d'Open Interest"""
        alerts = []
        
        if market_data.open_interest_change is None:
            return alerts
        
        oi_change = market_data.open_interest_change
        
        # Augmentation importante
        if oi_change >= 10:  # +10%
            alerts.append(Alert(
                alert_type=AlertType.OI_CHANGE,
                alert_level=AlertLevel.INFO,
                symbol=market_data.symbol,
                message=f"Open Interest en hausse : +{oi_change:.1f}%",
                price=market_data.current_price.price_eur,
                metadata={"oi_change_pct": oi_change}
            ))
        
        # Diminution importante
        elif oi_change <= -10:  # -10%
            alerts.append(Alert(
                alert_type=AlertType.OI_CHANGE,
                alert_level=AlertLevel.WARNING,
                symbol=market_data.symbol,
                message=f"Open Interest en baisse : {oi_change:.1f}%",
                price=market_data.current_price.price_eur,
                metadata={"oi_change_pct": oi_change}
            ))
        
        return alerts
    
    def _notify_callbacks(self, alert: Alert):
        """Notifie tous les callbacks enregistrés"""
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                # Log l'erreur mais continue avec les autres callbacks
                print(f"Erreur dans callback d'alerte: {e}")
    
    def get_recent_alerts(self, symbol: Optional[str] = None, limit: int = 10) -> List[Alert]:
        """Récupère les alertes récentes"""
        alerts = self.alert_history
        
        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol]
        
        # Trier par timestamp décroissant
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def clear_history(self):
        """Efface l'historique des alertes"""
        self.alert_history.clear()
        self.price_levels_triggered.clear()
