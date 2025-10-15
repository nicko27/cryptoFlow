"""
Database Models - Modèles SQLAlchemy pour persistance
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


class PriceHistory(Base):
    """Historique des prix"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    price_usd = Column(Float, nullable=False)
    price_eur = Column(Float, nullable=False)
    volume_24h = Column(Float)
    change_24h = Column(Float)
    high_24h = Column(Float)
    low_24h = Column(Float)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'price_usd': self.price_usd,
            'price_eur': self.price_eur,
            'volume_24h': self.volume_24h,
            'change_24h': self.change_24h,
            'timestamp': self.timestamp
        }


class AlertHistory(Base):
    """Historique des alertes"""
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(10), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    alert_level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    metadata = Column(JSON)
    acknowledged = Column(Boolean, default=False)
    sent_telegram = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TechnicalIndicatorHistory(Base):
    """Historique des indicateurs techniques"""
    __tablename__ = 'technical_indicator_history'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    ma20 = Column(Float)
    ma50 = Column(Float)
    ma200 = Column(Float)
    support = Column(Float)
    resistance = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)
    stochastic_k = Column(Float)
    stochastic_d = Column(Float)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PredictionHistory(Base):
    """Historique des prédictions"""
    __tablename__ = 'prediction_history'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    direction = Column(String(5))
    trend_score = Column(Integer)
    signals = Column(JSON)
    target_high = Column(Float)
    target_low = Column(Float)
    timeframe_short = Column(Float)
    timeframe_medium = Column(Float)
    timeframe_long = Column(Float)
    actual_price_short = Column(Float)  # Prix réel après short timeframe
    actual_price_medium = Column(Float)  # Prix réel après medium timeframe
    actual_price_long = Column(Float)  # Prix réel après long timeframe
    accuracy_short = Column(Float)  # Précision de la prédiction
    accuracy_medium = Column(Float)
    accuracy_long = Column(Float)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Portfolio(Base):
    """Portfolio de l'utilisateur"""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True)
    amount = Column(Float, nullable=False)  # Quantité de crypto
    entry_price_eur = Column(Float, nullable=False)
    current_price_eur = Column(Float, nullable=False)
    investment_eur = Column(Float, nullable=False)
    current_value_eur = Column(Float, nullable=False)
    gain_loss_eur = Column(Float, nullable=False)
    gain_loss_pct = Column(Float, nullable=False)
    entry_date = Column(DateTime(timezone=True), nullable=False)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    trades = relationship("Trade", back_populates="portfolio")


class Trade(Base):
    """Historique des trades"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolio.id'))
    symbol = Column(String(10), nullable=False, index=True)
    trade_type = Column(String(10), nullable=False)  # BUY, SELL
    amount = Column(Float, nullable=False)
    price_eur = Column(Float, nullable=False)
    total_eur = Column(Float, nullable=False)
    fee_eur = Column(Float, default=0.0)
    strategy = Column(String(50))  # Nom de la stratégie
    notes = Column(Text)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    portfolio = relationship("Portfolio", back_populates="trades")


class BacktestResult(Base):
    """Résultats de backtesting"""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    profit_factor = Column(Float)
    parameters = Column(JSON)  # Paramètres de la stratégie
    trades_data = Column(JSON)  # Détails des trades
    equity_curve = Column(JSON)  # Courbe d'équité
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MarketSentiment(Base):
    """Sentiment de marché (social, on-chain)"""
    __tablename__ = 'market_sentiment'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    fear_greed_index = Column(Integer)
    twitter_sentiment = Column(Float)  # -1 à 1
    reddit_sentiment = Column(Float)
    google_trends = Column(Float)
    whale_alerts = Column(Integer)  # Nombre d'alertes whale
    large_transactions = Column(Integer)
    exchange_inflow = Column(Float)
    exchange_outflow = Column(Float)
    active_addresses = Column(Integer)
    transaction_count = Column(Integer)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SystemStats(Base):
    """Statistiques du système"""
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True)
    checks_count = Column(Integer, default=0)
    alerts_sent = Column(Integer, default=0)
    predictions_made = Column(Integer, default=0)
    predictions_correct = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    uptime_seconds = Column(Integer, default=0)
    last_check = Column(DateTime(timezone=True))
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class StrategyPerformance(Base):
    """Performance des stratégies"""
    __tablename__ = 'strategy_performance'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(100), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    total_signals = Column(Integer, default=0)
    correct_signals = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    avg_return = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    last_signal_date = Column(DateTime(timezone=True))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
