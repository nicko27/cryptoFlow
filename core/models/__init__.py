"""
Models - Représentation des données du bot crypto
VERSION FINALE COMPLÈTE avec TOUS les champs du config.yaml
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum


class AlertType(Enum):
    """Types d'alertes"""
    PRICE_DROP = "price_drop"
    PRICE_SPIKE = "price_spike"
    LEVEL_CROSSED = "level_crossed"
    FUNDING_NEGATIVE = "funding_negative"
    OI_CHANGE = "oi_change"
    FEAR_GREED = "fear_greed"
    OPPORTUNITY = "opportunity"
    PREDICTION = "prediction"


class AlertLevel(Enum):
    """Niveaux de criticité"""
    INFO = "info"
    WARNING = "warning"
    IMPORTANT = "important"
    CRITICAL = "critical"


class PredictionType(Enum):
    """Types de prédictions"""
    BULLISH = "HAUSSIER"
    SLIGHTLY_BULLISH = "LÉGÈREMENT HAUSSIER"
    NEUTRAL = "NEUTRE"
    SLIGHTLY_BEARISH = "LÉGÈREMENT BAISSIER"
    BEARISH = "BAISSIER"


@dataclass
class CryptoPrice:
    """Prix d'une crypto à un instant T"""
    symbol: str
    price_usd: float
    price_eur: float
    timestamp: datetime
    volume_24h: float = 0.0
    change_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    
    def __post_init__(self):
        """FIXED: Assurer que timestamp est timezone-aware"""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class PriceLevel:
    """Niveau de prix configuré"""
    symbol: str
    level: float
    level_type: str
    buffer: float = 2.0
    cooldown_minutes: int = 30
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def can_trigger(self) -> bool:
        """Vérifie si le niveau peut être déclenché"""
        if self.last_triggered is None:
            return True
        
        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - self.last_triggered).total_seconds() / 60
        return elapsed_minutes >= self.cooldown_minutes
    
    def record_trigger(self):
        """Enregistre le déclenchement"""
        self.last_triggered = datetime.now(timezone.utc)
        self.trigger_count += 1


@dataclass
class TechnicalIndicators:
    """Indicateurs techniques"""
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0  # FIXED
    ma20: float = 0.0
    ma50: float = 0.0
    ma200: float = 0.0
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    volume_trend: str = "NEUTRAL"

    def __post_init__(self):
        """Harmonise les alias support/resistance"""
        if self.support_level is None and self.support is not None:
            self.support_level = self.support
        if self.resistance_level is None and self.resistance is not None:
            self.resistance_level = self.resistance
        if self.support is None and self.support_level is not None:
            self.support = self.support_level
        if self.resistance is None and self.resistance_level is not None:
            self.resistance = self.resistance_level


@dataclass
class MarketData:
    """Données complètes du marché"""
    symbol: str
    current_price: CryptoPrice
    technical_indicators: TechnicalIndicators
    price_change_24h: Optional[float] = None
    price_change_7d: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    open_interest: Optional[float] = None  # FIXED
    fear_greed_index: Optional[int] = None
    funding_rate: Optional[float] = None
    open_interest_change: Optional[float] = None
    weekly_change: Optional[float] = None
    price_history: List[CryptoPrice] = field(default_factory=list)
    
    def get_price_change(self, minutes: int) -> Optional[float]:
        """FIXED: Calcul avec timezone-aware"""
        if not self.price_history:
            return None
        
        now = datetime.now(timezone.utc)
        
        recent_prices = [
            p for p in self.price_history
            if p.timestamp.tzinfo is not None and
            (now - p.timestamp).total_seconds() / 60 <= minutes
        ]
        
        if not recent_prices or len(recent_prices) < 2:
            return None
        
        oldest = min(recent_prices, key=lambda p: p.timestamp)
        newest = max(recent_prices, key=lambda p: p.timestamp)
        
        if oldest.price_eur == 0:
            return None
        
        return ((newest.price_eur - oldest.price_eur) / oldest.price_eur) * 100


@dataclass
class Alert:
    """Alerte générée par le système"""
    alert_type: AlertType
    alert_level: AlertLevel  # FIXED: 'alert_level' au lieu de 'level'
    symbol: str
    message: str
    price: Optional[float] = None  # FIXED: 'price' au lieu de 'value'
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class Prediction:
    """Prédiction de marché"""
    symbol: str
    prediction_type: PredictionType
    confidence: int  # FIXED: int au lieu de float (0-100)
    direction: str
    trend_score: int  # FIXED: Obligatoire au lieu d'Optional
    signals: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    target_price_high: Optional[float] = None  # FIXED: Nom complet
    target_price_low: Optional[float] = None  # FIXED: Nom complet
    timeframe_short: str = "1h"  # FIXED: str au lieu de float
    timeframe_medium: str = "4h"  # FIXED: str au lieu de float
    timeframe_long: str = "24h"  # FIXED: str au lieu de float
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class OpportunityScore:
    """Score d'opportunité d'investissement"""
    symbol: str
    score: int  # 0-10
    recommendation: str  # BUY, SELL, HOLD
    confidence: int  # FIXED: Ajouté - 0-100
    reasons: List[str] = field(default_factory=list)  # FIXED: Ajouté
    risk_level: str = "MEDIUM"  # FIXED: Ajouté - LOW, MEDIUM, HIGH
    factors: Dict[str, Any] = field(default_factory=dict)
    buy_probability: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class BotConfiguration:
    """
    Configuration du bot - VERSION COMPLÈTE FINALE
    Tous les champs utilisés par config_manager.py
    """
    # === TELEGRAM ===
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_message_delay: float = 0.5
    telegram_show_prices: bool = True
    telegram_show_trend_24h: bool = True
    telegram_show_trend_7d: bool = True
    telegram_show_recommendations: bool = True
    
    # Thresholds Telegram
    trend_buy_threshold_24h: float = 2.0
    trend_sell_threshold_24h: float = -2.0
    trend_buy_threshold_7d: float = 5.0
    trend_sell_threshold_7d: float = -5.0
    
    # === CRYPTO ===
    crypto_symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    investment_amount: float = 100.0
    
    # === TIMING ===
    check_interval_seconds: int = 900
    summary_hours: List[int] = field(default_factory=lambda: [9, 12, 18])
    
    # === ALERTS ===
    enable_alerts: bool = True
    price_lookback_minutes: int = 120
    price_drop_threshold: float = 10.0
    price_spike_threshold: float = 10.0
    funding_negative_threshold: float = -0.03
    oi_delta_threshold: float = 3.0
    fear_greed_max: int = 30
    
    # RSI thresholds
    rsi_oversold: int = 30  # FIXED: Ajouté
    rsi_overbought: int = 70  # FIXED: Ajouté
    
    # Fear & Greed thresholds
    fear_greed_extreme_fear: int = 25  # FIXED: Ajouté
    fear_greed_extreme_greed: int = 75  # FIXED: Ajouté
    
    # === PRICE LEVELS ===
    enable_price_levels: bool = True
    price_levels: Dict[str, Dict[str, float]] = field(default_factory=dict)
    level_buffer_eur: float = 2.0
    level_cooldown_minutes: int = 30
    
    # === QUIET HOURS ===
    enable_quiet_hours: bool = False
    quiet_start_hour: int = 23
    quiet_end_hour: int = 7
    quiet_allow_critical: bool = True
    
    # Mode nuit (alias de quiet_hours pour rétrocompatibilité)
    enable_night_mode: bool = False  # FIXED: Ajouté
    night_mode_start_hour: int = 23  # FIXED: Ajouté
    night_mode_end_hour: int = 7  # FIXED: Ajouté
    
    # === FEATURES ===
    enable_graphs: bool = True
    show_levels_on_graph: bool = True
    enable_startup_summary: bool = True
    send_summary_chart: bool = False  # FIXED: Ajouté
    send_summary_dca: bool = False  # FIXED: Ajouté
    enable_opportunity_score: bool = True
    opportunity_threshold: int = 7
    enable_predictions: bool = True
    prediction_confidence_threshold: int = 60  # FIXED: Ajouté
    enable_timeline: bool = True
    enable_gain_loss_calc: bool = True
    enable_dca_suggestions: bool = True
    use_simple_language: bool = True  # FIXED: Nom corrigé
    educational_mode: bool = True
    detail_level: str = "normal"
    
    # Daily summary
    enable_daily_summary: bool = False  # FIXED: Ajouté
    daily_summary_hour: int = 9  # FIXED: Ajouté
    
    # DCA settings
    enable_dca: bool = False  # FIXED: Ajouté
    dca_amount_eur: float = 100.0  # FIXED: Ajouté
    dca_frequency_days: int = 7  # FIXED: Ajouté
    
    # Trend periods
    trend_short_days: int = 7  # FIXED: Ajouté
    trend_medium_days: int = 30  # FIXED: Ajouté
    trend_long_days: int = 90  # FIXED: Ajouté
    
    # === REPORT ===
    report_detail_level: str = "detailed"
    report_enabled_sections: Dict[str, bool] = field(default_factory=lambda: {  # FIXED: Nom corrigé
        "executive_summary": True,
        "per_crypto": True,
        "comparison": True,
        "recommendations": True,
        "advanced_analysis": True,
        "statistics": True,
    })
    report_advanced_metrics: Dict[str, bool] = field(default_factory=lambda: {  # FIXED: Nom corrigé
        "volatility": True,
        "drawdown": True,
        "trend_strength": True,
        "risk_score": True,
        "dca_projection": False,
        "correlation": False,
    })
    report_include_summary: bool = False
    report_include_telegram_report: bool = False
    report_include_chart: bool = False
    report_include_dca: bool = False
    report_include_broker_prices: bool = True
    
    # === BROKERS ===
    enabled_brokers: List[str] = field(default_factory=lambda: ["binance", "revolut"])
    broker_settings: Dict[str, Any] = field(default_factory=dict)  # FIXED: Nom corrigé
    
    # === NOTIFICATIONS ===
    notification_per_coin: bool = True  # FIXED: Nom corrigé
    notification_include_chart: bool = True  # FIXED: Nom corrigé
    notification_chart_timeframes: List[int] = field(default_factory=lambda: [24, 168])  # FIXED: Nom corrigé
    notification_include_brokers: bool = True  # FIXED: Nom corrigé
    notification_send_glossary: bool = True  # FIXED: Nom corrigé
    notification_thresholds: Dict[str, Any] = field(default_factory=dict)  # FIXED: Nom corrigé
    notification_content_by_coin: Dict[str, Any] = field(default_factory=dict)  # FIXED: Nom corrigé
    
    # === COINS ===
    coin_settings: Dict[str, Any] = field(default_factory=dict)  # FIXED: Nom corrigé
    
    # === MODES ===
    daemon_mode: bool = False
    gui_mode: bool = True
    
    # === DATABASE ===
    database_path: str = "data/crypto_bot.db"
    keep_history_days: int = 30
    
    # === LOGGING ===
    log_file: str = "logs/crypto_bot.log"
    log_level: str = "INFO"
    
    def is_quiet_time(self) -> bool:
        """Vérifie si on est en période de silence"""
        if not self.enable_quiet_hours:
            return False
        
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        
        if self.quiet_start_hour > self.quiet_end_hour:
            if current_hour >= self.quiet_start_hour or current_hour < self.quiet_end_hour:
                return True
        else:
            if self.quiet_start_hour <= current_hour < self.quiet_end_hour:
                return True
        
        return False


@dataclass
class BrokerQuote:
    """Cotations d'un courtier"""
    broker: str
    buy_price: float
    sell_price: float
    currency: str = "€"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position détenue dans le portfolio"""
    symbol: str
    amount: float
    entry_price_eur: float
    current_price_eur: float
    investment_eur: float
    current_value_eur: float = 0.0
    gain_loss_eur: float = 0.0
    gain_loss_pct: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.update_values(self.current_price_eur)

    def update_values(self, current_price_eur: float) -> None:
        """Met à jour les valeurs courantes de la position"""
        self.current_price_eur = current_price_eur
        self.current_value_eur = self.amount * current_price_eur
        self.gain_loss_eur = self.current_value_eur - self.investment_eur
        self.gain_loss_pct = (
            (self.gain_loss_eur / self.investment_eur) * 100
            if self.investment_eur else 0.0
        )
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class Portfolio:
    """Portfolio utilisateur"""
    positions: Dict[str, Position] = field(default_factory=dict)
    total_investment_eur: float = 0.0
    total_value_eur: float = 0.0
    total_gain_loss_eur: float = 0.0
    total_gain_loss_pct: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_position(self, position: Position) -> None:
        """Ajoute ou remplace une position dans le portfolio"""
        self.positions[position.symbol] = position
        self.recalculate()

    def recalculate(self) -> None:
        """Recalcule les agrégats du portfolio"""
        total_investment = sum(p.investment_eur for p in self.positions.values())
        total_value = sum(p.current_value_eur for p in self.positions.values())

        self.total_investment_eur = total_investment
        self.total_value_eur = total_value
        self.total_gain_loss_eur = total_value - total_investment
        self.total_gain_loss_pct = (
            (self.total_gain_loss_eur / total_investment) * 100
            if total_investment else 0.0
        )
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class SystemStatus:
    """Statut du système"""
    is_running: bool = False
    start_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    checks_count: int = 0
    alerts_sent: int = 0
    errors_count: int = 0
    
    def get_uptime_seconds(self) -> int:
        """Retourne l'uptime en secondes"""
        if not self.start_time:
            return 0
        
        return int((datetime.now(timezone.utc) - self.start_time).total_seconds())


# Exports
__all__ = [
    'AlertType',
    'AlertLevel',
    'PredictionType',
    'CryptoPrice',
    'PriceLevel',
    'TechnicalIndicators',
    'MarketData',
    'Alert',
    'Prediction',
    'OpportunityScore',
    'BotConfiguration',
    'BrokerQuote',
    'Position',
    'Portfolio',
    'SystemStatus',
]
