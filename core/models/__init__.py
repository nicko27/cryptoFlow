"""
Models - Représentation des données du bot crypto [TIMEZONE FIXED]
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
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        # Ensure timezone aware
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class PriceLevel:
    """Niveau de prix configuré"""
    symbol: str
    level: float
    level_type: str  # "low" ou "high"
    buffer: float = 2.0
    cooldown_minutes: int = 30
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def can_trigger(self) -> bool:
        """Vérifie si le niveau peut être déclenché"""
        if self.last_triggered is None:
            return True
        
        # FIX: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        # Ensure last_triggered is timezone-aware
        if self.last_triggered.tzinfo is None:
            self.last_triggered = self.last_triggered.replace(tzinfo=timezone.utc)
        
        elapsed = (now - self.last_triggered).total_seconds() / 60
        return elapsed >= self.cooldown_minutes
    
    def record_trigger(self):
        """Enregistre un déclenchement"""
        self.last_triggered = datetime.now(timezone.utc)
        self.trigger_count += 1


@dataclass
class TechnicalIndicators:
    """Indicateurs techniques"""
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    ma20: float = 0.0
    ma50: float = 0.0
    ma200: float = 0.0
    support: float = 0.0
    resistance: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    stochastic_k: float = 0.0
    stochastic_d: float = 0.0


@dataclass
class MarketData:
    """Données de marché complètes"""
    symbol: str
    current_price: CryptoPrice
    technical_indicators: TechnicalIndicators
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    fear_greed_index: Optional[int] = None
    price_history: List[CryptoPrice] = field(default_factory=list)
    
    def get_price_change(self, minutes: int) -> float:
        """Calcule le changement de prix sur N minutes"""
        if not self.price_history:
            return 0.0
        
        # FIX: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        recent_prices = [p for p in self.price_history 
                        if (now - p.timestamp).total_seconds() / 60 <= minutes]
        
        if not recent_prices:
            return 0.0
        
        oldest = min(recent_prices, key=lambda x: x.timestamp)
        return ((self.current_price.price_eur - oldest.price_eur) / oldest.price_eur) * 100


@dataclass
class Prediction:
    """Prédiction de marché"""
    prediction_type: PredictionType
    confidence: float
    direction: str  # 📈, 📉, ➡️
    trend_score: int
    signals: List[str] = field(default_factory=list)
    target_high: float = 0.0
    target_low: float = 0.0
    timeframe_short: float = 0.0  # 2-6h
    timeframe_medium: float = 0.0  # 1-2j
    timeframe_long: float = 0.0  # 1 sem
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OpportunityScore:
    """Score d'opportunité d'achat"""
    score: int  # 0-10
    reasons: List[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Alert:
    """Alerte générée"""
    alert_id: str
    symbol: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = f"{self.symbol}_{self.alert_type.value}_{int(self.timestamp.timestamp())}"


@dataclass
class Portfolio:
    """Portfolio de l'utilisateur"""
    total_investment_eur: float
    positions: Dict[str, 'Position'] = field(default_factory=dict)
    total_value_eur: float = 0.0
    total_gain_loss_eur: float = 0.0
    total_gain_loss_pct: float = 0.0
    
    def add_position(self, position: 'Position'):
        """Ajoute une position"""
        self.positions[position.symbol] = position
        self.recalculate()
    
    def recalculate(self):
        """Recalcule les totaux"""
        self.total_value_eur = sum(p.current_value_eur for p in self.positions.values())
        self.total_gain_loss_eur = sum(p.gain_loss_eur for p in self.positions.values())
        
        if self.total_investment_eur > 0:
            self.total_gain_loss_pct = (self.total_gain_loss_eur / self.total_investment_eur) * 100


@dataclass
class Position:
    """Position sur une crypto"""
    symbol: str
    amount: float  # Quantité de crypto
    entry_price_eur: float
    current_price_eur: float
    investment_eur: float
    current_value_eur: float = 0.0
    gain_loss_eur: float = 0.0
    gain_loss_pct: float = 0.0
    entry_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        self.update_values(self.current_price_eur)
    
    def update_values(self, current_price: float):
        """Met à jour les valeurs avec le prix actuel"""
        self.current_price_eur = current_price
        self.current_value_eur = self.amount * current_price
        self.gain_loss_eur = self.current_value_eur - self.investment_eur
        
        if self.investment_eur > 0:
            self.gain_loss_pct = (self.gain_loss_eur / self.investment_eur) * 100


@dataclass
class BotConfiguration:
    """Configuration complète du bot"""
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Cryptos surveillées
    crypto_symbols: List[str] = field(default_factory=lambda: ["BTC"])
    investment_amount: float = 100.0
    
    # Alertes
    enable_alerts: bool = True
    price_lookback_minutes: int = 120
    price_drop_threshold: float = 10.0
    price_spike_threshold: float = 10.0
    funding_negative_threshold: float = -0.03
    oi_delta_threshold: float = 3.0
    fear_greed_max: int = 30
    
    # Niveaux de prix
    enable_price_levels: bool = True
    price_levels: Dict[str, Dict[str, float]] = field(default_factory=dict)
    level_buffer_eur: float = 2.0
    level_cooldown_minutes: int = 30
    
    # Features intelligentes
    enable_opportunity_score: bool = True
    opportunity_threshold: int = 7
    enable_predictions: bool = True
    enable_timeline: bool = True
    enable_gain_loss_calc: bool = True
    enable_dca_suggestions: bool = True
    use_simple_language: bool = True
    educational_mode: bool = True
    
    # Timing
    check_interval_seconds: int = 900
    summary_hours: List[int] = field(default_factory=lambda: [9, 12, 18])
    enable_quiet_hours: bool = False
    quiet_start_hour: int = 23
    quiet_end_hour: int = 7
    quiet_allow_critical: bool = True
    
    # Display
    enable_graphs: bool = True
    show_levels_on_graph: bool = True
    enable_startup_summary: bool = True
    
    # Mode
    daemon_mode: bool = False
    gui_mode: bool = True
    detail_level: str = "normal"  # "simple", "normal", "detailed"
    
    # Logging
    log_file: str = "crypto_bot.log"
    log_level: str = "INFO"
    
    # Database
    database_path: str = "data/crypto_bot.db"
    keep_history_days: int = 30


@dataclass
class SystemStatus:
    """État du système"""
    is_running: bool = False
    start_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    checks_count: int = 0
    alerts_sent_count: int = 0
    errors_count: int = 0
    current_mode: str = "stopped"  # stopped, daemon, gui
