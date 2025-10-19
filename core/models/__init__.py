"""
Models - Représentation des données du bot crypto
FIXED: Problème 2 - Timezone aware/naive datetime corrigé
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone  # FIXED: Import simple de timezone
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
        # FIXED: Problème 2 - Assurer que timestamp est timezone-aware
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        # Si naive, ajouter UTC
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
        
        # FIXED: Problème 2 - Utiliser datetime timezone-aware
        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - self.last_triggered).total_seconds() / 60
        return elapsed_minutes >= self.cooldown_minutes


@dataclass
class TechnicalIndicators:
    """Indicateurs techniques"""
    rsi: float
    macd: float
    macd_signal: float
    ma20: float
    ma50: float
    ma200: float
    bollinger_upper: float
    bollinger_lower: float
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    volume_trend: str = "NEUTRAL"


@dataclass
class MarketData:
    """Données complètes du marché pour une crypto"""
    symbol: str
    current_price: CryptoPrice
    technical_indicators: TechnicalIndicators
    fear_greed_index: Optional[int] = None
    funding_rate: Optional[float] = None
    open_interest_change: Optional[float] = None
    price_history: List[CryptoPrice] = field(default_factory=list)
    
    def get_price_change(self, minutes: int) -> Optional[float]:
        """
        FIXED: Problème 2 - Calcul de changement avec datetimes timezone-aware
        Calcule le changement de prix sur X minutes
        """
        if not self.price_history:
            return None
        
        # FIXED: Utiliser datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Filtrer les prix récents avec timestamps timezone-aware
        recent_prices = [
            p for p in self.price_history
            if p.timestamp.tzinfo is not None and  # Vérifier que c'est timezone-aware
            (now - p.timestamp).total_seconds() / 60 <= minutes
        ]
        
        if not recent_prices or len(recent_prices) < 2:
            return None
        
        # Prix le plus ancien et le plus récent
        oldest = min(recent_prices, key=lambda p: p.timestamp)
        newest = max(recent_prices, key=lambda p: p.timestamp)
        
        if oldest.price_eur == 0:
            return None
        
        change_pct = ((newest.price_eur - oldest.price_eur) / oldest.price_eur) * 100
        return change_pct


@dataclass
class Alert:
    """Alerte générée par le système"""
    alert_type: AlertType
    alert_level: AlertLevel
    symbol: str
    message: str
    price: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # FIXED: Problème 2 - S'assurer que timestamp est timezone-aware
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class Prediction:
    """Prédiction de mouvement de prix"""
    symbol: str
    prediction_type: PredictionType
    confidence: int  # 0-100
    direction: str  # UP, DOWN, NEUTRAL
    trend_score: int  # -10 à +10
    signals: List[str] = field(default_factory=list)
    target_price_high: Optional[float] = None
    target_price_low: Optional[float] = None
    timeframe_short: str = "1h"
    timeframe_medium: str = "4h"
    timeframe_long: str = "24h"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        # FIXED: Problème 2 - S'assurer que timestamp est timezone-aware
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class OpportunityScore:
    """Score d'opportunité d'achat/vente"""
    symbol: str
    score: int  # 0-10
    recommendation: str  # BUY, SELL, HOLD
    confidence: int  # 0-100
    reasons: List[str] = field(default_factory=list)
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        # FIXED: Problème 2 - S'assurer que timestamp est timezone-aware
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class BotConfiguration:
    """Configuration du bot"""
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_message_delay: int = 2
    telegram_show_prices: bool = True
    telegram_show_trend_24h: bool = True
    telegram_show_trend_7d: bool = True
    telegram_show_recommendations: bool = True
    
    # Cryptos à surveiller
    crypto_symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    
    # Intervalles
    check_interval_seconds: int = 900  # 15 minutes
    
    # Alertes
    price_drop_threshold: float = 5.0  # %
    price_spike_threshold: float = 5.0  # %
    price_lookback_minutes: int = 60
    enable_price_levels: bool = True
    price_levels: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # RSI
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    
    # Fear & Greed
    fear_greed_extreme_fear: int = 25
    fear_greed_extreme_greed: int = 75
    
    # Prédictions
    enable_predictions: bool = True
    prediction_confidence_threshold: int = 60
    
    # Mode nuit
    enable_night_mode: bool = False
    night_mode_start_hour: int = 23
    night_mode_end_hour: int = 7
    
    # Résumés
    enable_startup_summary: bool = True
    enable_daily_summary: bool = False
    daily_summary_hour: int = 9
    
    # Base de données
    database_path: str = "data/crypto_bot.db"
    keep_history_days: int = 30
    
    # Logs
    log_file: str = "logs/crypto_bot.log"
    log_level: str = "INFO"
    
    # DCA
    enable_dca: bool = False
    dca_amount_eur: float = 100.0
    dca_frequency_days: int = 7
    
    # Autres
    investment_amount: float = 1000.0
    trend_short_days: int = 7
    trend_medium_days: int = 30
    trend_long_days: int = 90
    
    # Nouveaux paramètres pour notifications avancées
    detail_level: str = "normal"  # "minimal", "normal", "detailed"
    coin_settings: Dict[str, Any] = field(default_factory=dict)
    notification_content_by_coin: Dict[str, Any] = field(default_factory=dict)


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
        
        # FIXED: Problème 2 - Utiliser timezone.utc
        return int((datetime.now(timezone.utc) - self.start_time).total_seconds())
