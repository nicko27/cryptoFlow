"""
Alert Service - Gestion des alertes [WITH OPEN INTEREST + IMPROVED ERROR HANDLING]
"""

from typing import List, Optional, Callable, Dict
from datetime import datetime, timezone
from core.models import (
    BotConfiguration, MarketData, Alert, AlertType,
    AlertLevel, Prediction, PriceLevel
)


class AlertService:
    """Service de gestion des alertes"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.price_levels: Dict[str, List[PriceLevel]] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Open Interest baseline tracking
        self.oi_baseline: Dict[str, float] = {}
        self.oi_last_check: Dict[str, datetime] = {}
        
        self._setup_price_levels()
    
    def _setup_price_levels(self):
        """Configure les niveaux de prix à surveiller"""
        if not self.config.enable_price_levels:
            return
        
        for symbol, levels in self.config.price_levels.items():
            if symbol not in self.price_levels:
                self.price_levels[symbol] = []
            
            if "low" in levels and levels["low"] > 0:
                self.price_levels[symbol].append(PriceLevel(
                    symbol=symbol,
                    level=levels["low"],
                    level_type="low",
                    buffer=self.config.level_buffer_eur,
                    cooldown_minutes=self.config.level_cooldown_minutes
                ))
            
            if "high" in levels and levels["high"] > 0:
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
        """Déclenche tous les callbacks avec gestion d'erreur"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"⚠️ Erreur callback alerte {alert.alert_id}: {e}")
    
    def check_alerts(self, market_data: MarketData, prediction: Optional[Prediction] = None) -> List[Alert]:
        """
        Vérifie toutes les conditions d'alerte avec gestion d'erreur robuste
        
        Args:
            market_data: Données de marché
            prediction: Prédiction (optionnel)
        
        Returns:
            Liste des alertes générées
        """
        alerts = []
        
        # Alertes de pourcentage de prix
        if self.config.enable_alerts:
            try:
                price_alerts = self._check_price_alerts(market_data)
                alerts.extend(price_alerts)
            except Exception as e:
                print(f"⚠️ Erreur check price alerts {market_data.symbol}: {e}")
        
        # Alertes de niveaux de prix
        if self.config.enable_price_levels:
            try:
                level_alerts = self._check_price_levels(market_data)
                alerts.extend(level_alerts)
            except Exception as e:
                print(f"⚠️ Erreur check price levels {market_data.symbol}: {e}")
        
        # Alertes sur dérivés
        try:
            funding_alerts = self._check_funding_rate(market_data)
            alerts.extend(funding_alerts)
        except Exception as e:
            print(f"⚠️ Erreur check funding {market_data.symbol}: {e}")
        
        try:
            oi_alerts = self._check_open_interest(market_data)
            alerts.extend(oi_alerts)
        except Exception as e:
            print(f"⚠️ Erreur check OI {market_data.symbol}: {e}")
        
        # Alertes Fear & Greed
        try:
            fgi_alerts = self._check_fear_greed(market_data)
            alerts.extend(fgi_alerts)
        except Exception as e:
            print(f"⚠️ Erreur check FGI {market_data.symbol}: {e}")
        
        # Alertes sur prédictions
        if prediction and self.config.enable_predictions:
            try:
                pred_alerts = self._check_prediction(market_data, prediction)
                alerts.extend(pred_alerts)
            except Exception as e:
                print(f"⚠️ Erreur check prediction {market_data.symbol}: {e}")
        
        # Sauvegarder et déclencher callbacks
        for alert in alerts:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            self._trigger_callbacks(alert)
        
        # Nettoyer l'historique (garder 1000 dernières)
        self.alert_history = self.alert_history[-1000:]
        
        return alerts
    
    def _check_price_alerts(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les alertes de changement de prix"""
        alerts = []
        
        try:
            change = market_data.get_price_change(self.config.price_lookback_minutes)
        except Exception as e:
            print(f"⚠️ Impossible de calculer price_change pour {market_data.symbol}: {e}")
            return alerts
        
        # Chute de prix
        if change <= -abs(self.config.price_drop_threshold):
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.PRICE_DROP,
                alert_level=AlertLevel.IMPORTANT,
                message=f"🔻 Chute de {change:.1f}% en {self.config.price_lookback_minutes} min → {market_data.current_price.price_eur:.2f}€",
                metadata={
                    "change_pct": change,
                    "lookback_minutes": self.config.price_lookback_minutes,
                    "current_price": market_data.current_price.price_eur
                }
            )
            alerts.append(alert)
        
        # Hausse de prix
        if change >= abs(self.config.price_spike_threshold):
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.PRICE_SPIKE,
                alert_level=AlertLevel.INFO,
                message=f"🚀 Hausse de +{change:.1f}% en {self.config.price_lookback_minutes} min → {market_data.current_price.price_eur:.2f}€",
                metadata={
                    "change_pct": change,
                    "lookback_minutes": self.config.price_lookback_minutes,
                    "current_price": market_data.current_price.price_eur
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_price_levels(self, market_data: MarketData) -> List[Alert]:
        """Vérifie les niveaux de prix configurés"""
        alerts = []
        
        symbol = market_data.symbol
        if symbol not in self.price_levels:
            return alerts
        
        current_price = market_data.current_price.price_eur
        
        for price_level in self.price_levels[symbol]:
            if not price_level.can_trigger():
                continue
            
            # Niveau bas atteint
            if price_level.level_type == "low":
                if current_price <= price_level.level:
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.IMPORTANT,
                        message=f"📍 {symbol} atteint le niveau BAS {price_level.level}€ (maintenant {current_price:.2f}€)",
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
            
            # Niveau haut atteint
            elif price_level.level_type == "high":
                if current_price >= price_level.level:
                    alert = Alert(
                        alert_id="",
                        symbol=symbol,
                        alert_type=AlertType.LEVEL_CROSSED,
                        alert_level=AlertLevel.IMPORTANT,
                        message=f"📍 {symbol} atteint le niveau HAUT {price_level.level}€ (maintenant {current_price:.2f}€)",
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
                message=f"💰 Funding négatif : {market_data.funding_rate:.4f}% (longs paient shorts)",
                metadata={"funding_rate": market_data.funding_rate}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_open_interest(self, market_data: MarketData) -> List[Alert]:
        """Vérifie l'Open Interest avec baseline tracking et cooldown"""
        alerts = []
        
        if market_data.open_interest is None:
            return alerts
        
        symbol = market_data.symbol
        current_oi = market_data.open_interest
        now = datetime.now(timezone.utc)
        
        # Cooldown de 1h entre vérifications OI
        if symbol in self.oi_last_check:
            elapsed = (now - self.oi_last_check[symbol]).total_seconds() / 3600
            if elapsed < 1.0:
                return alerts
        
        # Initialiser la baseline si nécessaire
        if symbol not in self.oi_baseline:
            self.oi_baseline[symbol] = current_oi
            self.oi_last_check[symbol] = now
            return alerts
        
        # Calculer le changement
        baseline = self.oi_baseline[symbol]
        if baseline > 0:
            change_pct = ((current_oi - baseline) / baseline) * 100
            
            # Alerte si changement significatif
            if abs(change_pct) >= self.config.oi_delta_threshold:
                if change_pct > 0:
                    emoji = "📈"
                    trend = "augmentation"
                else:
                    emoji = "📉"
                    trend = "diminution"
                
                level = AlertLevel.WARNING if abs(change_pct) > 5 else AlertLevel.INFO
                
                alert = Alert(
                    alert_id="",
                    symbol=symbol,
                    alert_type=AlertType.OI_CHANGE,
                    alert_level=level,
                    message=f"{emoji} Open Interest: {trend} de {abs(change_pct):.1f}% (intérêt {'croissant' if change_pct > 0 else 'décroissant'})",
                    metadata={
                        "current_oi": current_oi,
                        "baseline_oi": baseline,
                        "change_pct": change_pct
                    }
                )
                alerts.append(alert)
                self.oi_last_check[symbol] = now
        
        # Mettre à jour la baseline (moyenne mobile)
        self.oi_baseline[symbol] = (baseline * 0.9 + current_oi * 0.1)
        
        return alerts
    
    def _check_fear_greed(self, market_data: MarketData) -> List[Alert]:
        """Vérifie le Fear & Greed Index avec messages améliorés"""
        alerts = []
        
        if market_data.fear_greed_index is None:
            return alerts
        
        fgi = market_data.fear_greed_index
        
        # Peur extrême (opportunité d'achat)
        if fgi <= self.config.fear_greed_max:
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.INFO,
                message=f"😱 Peur extrême : {fgi}/100 (opportunité d'achat potentielle)",
                metadata={"fgi": fgi, "sentiment": "extreme_fear"}
            )
            alerts.append(alert)
        
        # Cupidité extrême (prudence)
        elif fgi >= 80:
            alert = Alert(
                alert_id="",
                symbol=market_data.symbol,
                alert_type=AlertType.FEAR_GREED,
                alert_level=AlertLevel.WARNING,
                message=f"🤑 Cupidité extrême : {fgi}/100 (prudence recommandée)",
                metadata={"fgi": fgi, "sentiment": "extreme_greed"}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_prediction(self, market_data: MarketData, prediction: Prediction) -> List[Alert]:
        """Vérifie les prédictions avec emojis améliorés"""
        alerts = []
        
        # Signal fort
        if prediction.confidence >= 70:
            if "HAUSSIER" in prediction.prediction_type.value:
                alert = Alert(
                    alert_id="",
                    symbol=market_data.symbol,
                    alert_type=AlertType.PREDICTION,
                    alert_level=AlertLevel.INFO,
                    message=f"📈 Signal haussier fort ({prediction.confidence:.0f}%) - Tendance à la hausse probable",
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
                    message=f"📉 Signal baissier fort ({prediction.confidence:.0f}%) - Tendance à la baisse probable",
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
