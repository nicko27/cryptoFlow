"""
Smart Alerts - Système d'alertes intelligentes avancées
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta, timezone, timezone
from dataclasses import dataclass
import numpy as np

from core.models import MarketData, CryptoPrice, Alert, AlertType, AlertLevel
from ml.ml_predictor import PatternRecognition


@dataclass
class SmartAlert:
    """Alerte intelligente avec contexte enrichi"""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    recommendation: str
    confidence: float
    signals: List[str]
    timestamp: datetime
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'signals': self.signals,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class SmartAlertSystem:
    """Système d'alertes intelligentes"""
    
    def __init__(self):
        self.pattern_recognizer = PatternRecognition()
        self.alert_history: List[SmartAlert] = []
        self.volume_baseline: Dict[str, float] = {}
        self.price_baseline: Dict[str, float] = {}
    
    def check_all_alerts(self, market_data: MarketData) -> List[SmartAlert]:
        """Vérifie toutes les conditions d'alerte intelligentes"""
        alerts = []
        
        # 1. Pattern recognition
        pattern_alerts = self._check_chart_patterns(market_data)
        alerts.extend(pattern_alerts)
        
        # 2. Volume spikes
        volume_alerts = self._check_volume_anomalies(market_data)
        alerts.extend(volume_alerts)
        
        # 3. Multi-indicator confluence
        confluence_alerts = self._check_indicator_confluence(market_data)
        alerts.extend(confluence_alerts)
        
        # 4. Divergences
        divergence_alerts = self._check_divergences(market_data)
        alerts.extend(divergence_alerts)
        
        # 5. Volatility spikes
        volatility_alerts = self._check_volatility_spikes(market_data)
        alerts.extend(volatility_alerts)
        
        # 6. Support/Resistance tests
        sr_alerts = self._check_support_resistance_tests(market_data)
        alerts.extend(sr_alerts)
        
        # Sauvegarder dans l'historique
        self.alert_history.extend(alerts)
        self.alert_history = self.alert_history[-1000:]  # Garder les 1000 dernières
        
        return alerts
    
    def _check_chart_patterns(self, market_data: MarketData) -> List[SmartAlert]:
        """Détecte les patterns chartistes"""
        alerts = []
        
        if len(market_data.price_history) < 50:
            return alerts
        
        prices = [p.price_eur for p in market_data.price_history]
        
        # Head and Shoulders (bearish)
        if self.pattern_recognizer.detect_head_and_shoulders(prices):
            alert = SmartAlert(
                alert_type='PATTERN_HEAD_SHOULDERS',
                severity='HIGH',
                message=f"🎯 Pattern Tête-Épaules détecté sur {market_data.symbol}",
                recommendation="Signal baissier fort - Envisager une vente ou un stop loss",
                confidence=75.0,
                signals=['Pattern Tête-Épaules', 'Signal baissier'],
                timestamp=datetime.now(timezone.utc),
                metadata={'pattern': 'head_and_shoulders', 'symbol': market_data.symbol}
            )
            alerts.append(alert)
        
        # Double Bottom (bullish)
        if self.pattern_recognizer.detect_double_bottom(prices):
            alert = SmartAlert(
                alert_type='PATTERN_DOUBLE_BOTTOM',
                severity='MEDIUM',
                message=f"🎯 Double Bottom détecté sur {market_data.symbol}",
                recommendation="Signal haussier - Opportunité d'achat potentielle",
                confidence=70.0,
                signals=['Double Bottom', 'Signal haussier'],
                timestamp=datetime.now(timezone.utc),
                metadata={'pattern': 'double_bottom', 'symbol': market_data.symbol}
            )
            alerts.append(alert)
        
        # Golden/Death Cross
        if len(market_data.price_history) >= 2:
            ti_current = market_data.technical_indicators
            
            # Simuler les indicateurs précédents (simplifié)
            prev_prices = [p.price_eur for p in market_data.price_history[:-1]]
            ma50_prev = np.mean(prev_prices[-50:]) if len(prev_prices) >= 50 else 0
            ma200_prev = np.mean(prev_prices[-200:]) if len(prev_prices) >= 200 else 0
            
            if self.pattern_recognizer.detect_golden_cross(
                ti_current.ma50, ti_current.ma200, ma50_prev, ma200_prev
            ):
                alert = SmartAlert(
                    alert_type='GOLDEN_CROSS',
                    severity='HIGH',
                    message=f"✨ Golden Cross sur {market_data.symbol}",
                    recommendation="Signal haussier majeur - Forte opportunité d'achat",
                    confidence=80.0,
                    signals=['Golden Cross', 'MA50 > MA200'],
                    timestamp=datetime.now(timezone.utc),
                    metadata={'ma50': ti_current.ma50, 'ma200': ti_current.ma200}
                )
                alerts.append(alert)
            
            if self.pattern_recognizer.detect_death_cross(
                ti_current.ma50, ti_current.ma200, ma50_prev, ma200_prev
            ):
                alert = SmartAlert(
                    alert_type='DEATH_CROSS',
                    severity='HIGH',
                    message=f"💀 Death Cross sur {market_data.symbol}",
                    recommendation="Signal baissier majeur - Envisager la sortie",
                    confidence=80.0,
                    signals=['Death Cross', 'MA50 < MA200'],
                    timestamp=datetime.now(timezone.utc),
                    metadata={'ma50': ti_current.ma50, 'ma200': ti_current.ma200}
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_volume_anomalies(self, market_data: MarketData) -> List[SmartAlert]:
        """Détecte les anomalies de volume"""
        alerts = []
        
        symbol = market_data.symbol
        current_volume = market_data.current_price.volume_24h
        
        # Établir la baseline si nécessaire
        if symbol not in self.volume_baseline:
            if len(market_data.price_history) >= 20:
                volumes = [p.volume_24h for p in market_data.price_history[-20:]]
                self.volume_baseline[symbol] = np.mean(volumes)
            else:
                return alerts
        
        baseline = self.volume_baseline[symbol]
        
        # Spike de volume (> 2x la baseline)
        if current_volume > baseline * 2:
            severity = 'HIGH' if current_volume > baseline * 3 else 'MEDIUM'
            
            alert = SmartAlert(
                alert_type='VOLUME_SPIKE',
                severity=severity,
                message=f"📊 Volume exceptionnel sur {symbol} ({current_volume/baseline:.1f}x normal)",
                recommendation="Activité inhabituelle - Vérifier les actualités",
                confidence=85.0,
                signals=[f'Volume {current_volume/baseline:.1f}x supérieur à la moyenne'],
                timestamp=datetime.now(timezone.utc),
                metadata={'current_volume': current_volume, 'baseline': baseline}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_indicator_confluence(self, market_data: MarketData) -> List[SmartAlert]:
        """Vérifie la confluence de plusieurs indicateurs"""
        alerts = []
        
        ti = market_data.technical_indicators
        bullish_signals = []
        bearish_signals = []
        
        # RSI
        if ti.rsi < 30:
            bullish_signals.append('RSI survendu')
        elif ti.rsi > 70:
            bearish_signals.append('RSI suracheté')
        
        # MACD
        if ti.macd_histogram > 0:
            bullish_signals.append('MACD positif')
        else:
            bearish_signals.append('MACD négatif')
        
        # MA
        current_price = market_data.current_price.price_eur
        if ti.ma20 > 0 and ti.ma50 > 0:
            if current_price > ti.ma20 > ti.ma50:
                bullish_signals.append('Prix > MA20 > MA50')
            elif current_price < ti.ma20 < ti.ma50:
                bearish_signals.append('Prix < MA20 < MA50')
        
        # Support/Resistance
        if ti.support > 0 and abs(current_price - ti.support) / current_price < 0.02:
            bullish_signals.append('Proche du support')
        
        if ti.resistance > 0 and abs(ti.resistance - current_price) / current_price < 0.02:
            bearish_signals.append('Proche de la résistance')
        
        # Confluence bullish
        if len(bullish_signals) >= 3:
            alert = SmartAlert(
                alert_type='BULLISH_CONFLUENCE',
                severity='HIGH',
                message=f"🚀 Confluence haussière sur {market_data.symbol}",
                recommendation="Plusieurs indicateurs convergent à la hausse",
                confidence=75.0 + len(bullish_signals) * 5,
                signals=bullish_signals,
                timestamp=datetime.now(timezone.utc),
                metadata={'num_signals': len(bullish_signals)}
            )
            alerts.append(alert)
        
        # Confluence bearish
        if len(bearish_signals) >= 3:
            alert = SmartAlert(
                alert_type='BEARISH_CONFLUENCE',
                severity='HIGH',
                message=f"📉 Confluence baissière sur {market_data.symbol}",
                recommendation="Plusieurs indicateurs convergent à la baisse",
                confidence=75.0 + len(bearish_signals) * 5,
                signals=bearish_signals,
                timestamp=datetime.now(timezone.utc),
                metadata={'num_signals': len(bearish_signals)}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_divergences(self, market_data: MarketData) -> List[SmartAlert]:
        """Détecte les divergences RSI/Prix"""
        alerts = []
        
        if len(market_data.price_history) < 20:
            return alerts
        
        # Simplifié - dans une vraie implémentation, on comparerait les pics/creux
        prices = [p.price_eur for p in market_data.price_history[-20:]]
        
        # Prix fait un nouveau bas mais RSI ne confirme pas (bullish divergence)
        if prices[-1] == min(prices[-10:]) and market_data.technical_indicators.rsi > 35:
            alert = SmartAlert(
                alert_type='BULLISH_DIVERGENCE',
                severity='MEDIUM',
                message=f"💡 Divergence haussière possible sur {market_data.symbol}",
                recommendation="Le prix baisse mais le RSI ne confirme pas - Possible retournement",
                confidence=65.0,
                signals=['Nouveau bas du prix', 'RSI ne confirme pas'],
                timestamp=datetime.now(timezone.utc),
                metadata={'rsi': market_data.technical_indicators.rsi}
            )
            alerts.append(alert)
        
        # Prix fait un nouveau haut mais RSI ne confirme pas (bearish divergence)
        if prices[-1] == max(prices[-10:]) and market_data.technical_indicators.rsi < 65:
            alert = SmartAlert(
                alert_type='BEARISH_DIVERGENCE',
                severity='MEDIUM',
                message=f"⚠️ Divergence baissière possible sur {market_data.symbol}",
                recommendation="Le prix monte mais le RSI ne confirme pas - Possible retournement",
                confidence=65.0,
                signals=['Nouveau haut du prix', 'RSI ne confirme pas'],
                timestamp=datetime.now(timezone.utc),
                metadata={'rsi': market_data.technical_indicators.rsi}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_volatility_spikes(self, market_data: MarketData) -> List[SmartAlert]:
        """Détecte les pics de volatilité"""
        alerts = []
        
        if len(market_data.price_history) < 20:
            return alerts
        
        # Calculer la volatilité récente
        prices = [p.price_eur for p in market_data.price_history[-20:]]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        recent_volatility = np.std(returns[-5:]) if len(returns) >= 5 else 0
        baseline_volatility = np.std(returns)
        
        # Spike de volatilité
        if recent_volatility > baseline_volatility * 2:
            alert = SmartAlert(
                alert_type='VOLATILITY_SPIKE',
                severity='MEDIUM',
                message=f"⚡ Volatilité accrue sur {market_data.symbol}",
                recommendation="Marché agité - Prudence recommandée",
                confidence=80.0,
                signals=[f'Volatilité {recent_volatility/baseline_volatility:.1f}x supérieure'],
                timestamp=datetime.now(timezone.utc),
                metadata={'volatility_ratio': recent_volatility/baseline_volatility}
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_support_resistance_tests(self, market_data: MarketData) -> List[SmartAlert]:
        """Détecte les tests de support/résistance"""
        alerts = []
        
        ti = market_data.technical_indicators
        current_price = market_data.current_price.price_eur
        
        # Test de support
        if ti.support > 0:
            distance_support = (current_price - ti.support) / current_price * 100
            
            if 0 < distance_support < 1:  # À moins de 1% du support
                alert = SmartAlert(
                    alert_type='SUPPORT_TEST',
                    severity='MEDIUM',
                    message=f"🎯 Test du support {ti.support:.2f}€ sur {market_data.symbol}",
                    recommendation="Zone de support critique - Attention au rebond ou cassure",
                    confidence=70.0,
                    signals=[f'Prix à {distance_support:.2f}% du support'],
                    timestamp=datetime.now(timezone.utc),
                    metadata={'support': ti.support, 'current_price': current_price}
                )
                alerts.append(alert)
        
        # Test de résistance
        if ti.resistance > 0:
            distance_resistance = (ti.resistance - current_price) / current_price * 100
            
            if 0 < distance_resistance < 1:  # À moins de 1% de la résistance
                alert = SmartAlert(
                    alert_type='RESISTANCE_TEST',
                    severity='MEDIUM',
                    message=f"🎯 Test de la résistance {ti.resistance:.2f}€ sur {market_data.symbol}",
                    recommendation="Zone de résistance critique - Attention au rejet ou breakout",
                    confidence=70.0,
                    signals=[f'Prix à {distance_resistance:.2f}% de la résistance'],
                    timestamp=datetime.now(timezone.utc),
                    metadata={'resistance': ti.resistance, 'current_price': current_price}
                )
                alerts.append(alert)
        
        return alerts
    
    def get_alert_summary(self, hours: int = 24) -> Dict:
        """Résumé des alertes sur une période"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_alerts = [a for a in self.alert_history if a.timestamp >= cutoff]
        
        if not recent_alerts:
            return {'total': 0, 'by_severity': {}, 'by_type': {}}
        
        # Par sévérité
        by_severity = {}
        for alert in recent_alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
        
        # Par type
        by_type = {}
        for alert in recent_alerts:
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1
        
        return {
            'total': len(recent_alerts),
            'by_severity': by_severity,
            'by_type': by_type,
            'most_common_type': max(by_type, key=by_type.get) if by_type else None
        }
