"""
Database Repository - Gestion des interactions avec la base de données
"""

from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone, timezone
from pathlib import Path

from database.models import (
    Base, PriceHistory, AlertHistory, TechnicalIndicatorHistory,
    PredictionHistory, Portfolio, Trade, BacktestResult,
    MarketSentiment, SystemStats, StrategyPerformance
)
from core.models import (
    CryptoPrice, Alert, TechnicalIndicators, Prediction,
    MarketData
)


class DatabaseRepository:
    """Repository pour gérer toutes les opérations de base de données"""
    
    def __init__(self, database_path: str = "data/crypto_bot.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Créer engine SQLite
        self.engine = create_engine(
            f'sqlite:///{self.database_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        
        # Créer toutes les tables
        Base.metadata.create_all(self.engine)
        
        # Session factory
        self.Session = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager pour sessions"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ========== PRICE HISTORY ==========
    
    def save_price(self, price: CryptoPrice):
        """Sauvegarde un prix"""
        with self.get_session() as session:
            price_record = PriceHistory(
                symbol=price.symbol,
                price_usd=price.price_usd,
                price_eur=price.price_eur,
                volume_24h=price.volume_24h,
                change_24h=price.change_24h,
                high_24h=price.high_24h,
                low_24h=price.low_24h,
                timestamp=price.timestamp
            )
            session.add(price_record)
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[CryptoPrice]:
        """Récupère l'historique des prix"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self.get_session() as session:
            records = session.query(PriceHistory).filter(
                and_(
                    PriceHistory.symbol == symbol,
                    PriceHistory.timestamp >= cutoff
                )
            ).order_by(PriceHistory.timestamp.asc()).all()
            
            return [
                CryptoPrice(
                    symbol=r.symbol,
                    price_usd=r.price_usd,
                    price_eur=r.price_eur,
                    timestamp=r.timestamp,
                    volume_24h=r.volume_24h,
                    change_24h=r.change_24h,
                    high_24h=r.high_24h,
                    low_24h=r.low_24h
                )
                for r in records
            ]
    
    def cleanup_old_prices(self, days: int = 30):
        """Nettoie les anciens prix"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.get_session() as session:
            deleted = session.query(PriceHistory).filter(
                PriceHistory.timestamp < cutoff
            ).delete()
            return deleted
    
    # ========== ALERTS ==========
    
    def save_alert(self, alert: Alert):
        """Sauvegarde une alerte"""
        with self.get_session() as session:
            alert_record = AlertHistory(
                alert_id=alert.alert_id,
                symbol=alert.symbol,
                alert_type=alert.alert_type.value,
                alert_level=alert.alert_level.value,
                message=alert.message,
                metadata=alert.metadata,
                acknowledged=alert.acknowledged,
                sent_telegram=False,
                timestamp=alert.timestamp
            )
            session.add(alert_record)
    
    def get_alert_history(self, symbol: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Récupère l'historique des alertes"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self.get_session() as session:
            query = session.query(AlertHistory).filter(
                AlertHistory.timestamp >= cutoff
            )
            
            if symbol:
                query = query.filter(AlertHistory.symbol == symbol)
            
            records = query.order_by(AlertHistory.timestamp.desc()).all()
            
            return [
                {
                    'alert_id': r.alert_id,
                    'symbol': r.symbol,
                    'alert_type': r.alert_type,
                    'alert_level': r.alert_level,
                    'message': r.message,
                    'timestamp': r.timestamp,
                    'acknowledged': r.acknowledged
                }
                for r in records
            ]
    
    def mark_alert_sent(self, alert_id: str):
        """Marque une alerte comme envoyée"""
        with self.get_session() as session:
            session.query(AlertHistory).filter(
                AlertHistory.alert_id == alert_id
            ).update({'sent_telegram': True})
    
    # ========== TECHNICAL INDICATORS ==========
    
    def save_technical_indicators(self, symbol: str, indicators: TechnicalIndicators, timestamp: datetime):
        """Sauvegarde les indicateurs techniques"""
        with self.get_session() as session:
            record = TechnicalIndicatorHistory(
                symbol=symbol,
                rsi=indicators.rsi,
                macd=indicators.macd,
                macd_signal=indicators.macd_signal,
                macd_histogram=indicators.macd_histogram,
                ma20=indicators.ma20,
                ma50=indicators.ma50,
                ma200=indicators.ma200,
                support=indicators.support,
                resistance=indicators.resistance,
                bollinger_upper=indicators.bollinger_upper,
                bollinger_lower=indicators.bollinger_lower,
                stochastic_k=indicators.stochastic_k,
                stochastic_d=indicators.stochastic_d,
                timestamp=timestamp
            )
            session.add(record)
    
    # ========== PREDICTIONS ==========
    
    def save_prediction(self, symbol: str, prediction: Prediction):
        """Sauvegarde une prédiction"""
        with self.get_session() as session:
            record = PredictionHistory(
                symbol=symbol,
                prediction_type=prediction.prediction_type.value,
                confidence=prediction.confidence,
                direction=prediction.direction,
                trend_score=prediction.trend_score,
                signals=prediction.signals,
                target_high=prediction.target_high,
                target_low=prediction.target_low,
                timeframe_short=prediction.timeframe_short,
                timeframe_medium=prediction.timeframe_medium,
                timeframe_long=prediction.timeframe_long,
                timestamp=prediction.timestamp
            )
            session.add(record)
            session.flush()
            return record.id
    
    def update_prediction_accuracy(self, prediction_id: int, 
                                   actual_price_short: Optional[float] = None,
                                   actual_price_medium: Optional[float] = None,
                                   actual_price_long: Optional[float] = None):
        """Met à jour la précision d'une prédiction"""
        with self.get_session() as session:
            prediction = session.query(PredictionHistory).filter(
                PredictionHistory.id == prediction_id
            ).first()
            
            if not prediction:
                return
            
            if actual_price_short is not None:
                prediction.actual_price_short = actual_price_short
                # Calculer accuracy
                predicted = prediction.timeframe_short
                error = abs(predicted - actual_price_short) / actual_price_short
                prediction.accuracy_short = max(0, 100 - error * 100)
            
            if actual_price_medium is not None:
                prediction.actual_price_medium = actual_price_medium
                predicted = prediction.timeframe_medium
                error = abs(predicted - actual_price_medium) / actual_price_medium
                prediction.accuracy_medium = max(0, 100 - error * 100)
            
            if actual_price_long is not None:
                prediction.actual_price_long = actual_price_long
                predicted = prediction.timeframe_long
                error = abs(predicted - actual_price_long) / actual_price_long
                prediction.accuracy_long = max(0, 100 - error * 100)
    
    def get_prediction_accuracy_stats(self, symbol: Optional[str] = None, days: int = 30) -> Dict:
        """Récupère les stats de précision des prédictions"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.get_session() as session:
            query = session.query(PredictionHistory).filter(
                and_(
                    PredictionHistory.timestamp >= cutoff,
                    PredictionHistory.accuracy_short.isnot(None)
                )
            )
            
            if symbol:
                query = query.filter(PredictionHistory.symbol == symbol)
            
            predictions = query.all()
            
            if not predictions:
                return {'total': 0, 'avg_accuracy': 0}
            
            accuracies = [p.accuracy_short for p in predictions if p.accuracy_short is not None]
            
            return {
                'total': len(predictions),
                'avg_accuracy': sum(accuracies) / len(accuracies) if accuracies else 0,
                'min_accuracy': min(accuracies) if accuracies else 0,
                'max_accuracy': max(accuracies) if accuracies else 0
            }
    
    # ========== PORTFOLIO ==========
    
    def save_portfolio_position(self, symbol: str, amount: float, entry_price: float,
                                current_price: float, investment: float, entry_date: datetime):
        """Sauvegarde ou met à jour une position de portfolio"""
        with self.get_session() as session:
            position = session.query(Portfolio).filter(
                Portfolio.symbol == symbol
            ).first()
            
            current_value = amount * current_price
            gain_loss = current_value - investment
            gain_loss_pct = (gain_loss / investment) * 100 if investment > 0 else 0
            
            if position:
                # Mise à jour
                position.amount = amount
                position.entry_price_eur = entry_price
                position.current_price_eur = current_price
                position.investment_eur = investment
                position.current_value_eur = current_value
                position.gain_loss_eur = gain_loss
                position.gain_loss_pct = gain_loss_pct
                position.last_updated = datetime.now(timezone.utc)
            else:
                # Création
                position = Portfolio(
                    symbol=symbol,
                    amount=amount,
                    entry_price_eur=entry_price,
                    current_price_eur=current_price,
                    investment_eur=investment,
                    current_value_eur=current_value,
                    gain_loss_eur=gain_loss,
                    gain_loss_pct=gain_loss_pct,
                    entry_date=entry_date,
                    last_updated=datetime.now(timezone.utc)
                )
                session.add(position)
    
    def get_portfolio(self) -> List[Dict]:
        """Récupère tout le portfolio"""
        with self.get_session() as session:
            positions = session.query(Portfolio).all()
            
            return [
                {
                    'symbol': p.symbol,
                    'amount': p.amount,
                    'entry_price_eur': p.entry_price_eur,
                    'current_price_eur': p.current_price_eur,
                    'investment_eur': p.investment_eur,
                    'current_value_eur': p.current_value_eur,
                    'gain_loss_eur': p.gain_loss_eur,
                    'gain_loss_pct': p.gain_loss_pct,
                    'entry_date': p.entry_date
                }
                for p in positions
            ]
    
    # ========== TRADES ==========
    
    def save_trade(self, symbol: str, trade_type: str, amount: float, price: float,
                  total: float, fee: float = 0.0, strategy: str = None, notes: str = None):
        """Sauvegarde un trade"""
        with self.get_session() as session:
            # Trouver le portfolio associé
            portfolio = session.query(Portfolio).filter(
                Portfolio.symbol == symbol
            ).first()
            
            trade = Trade(
                portfolio_id=portfolio.id if portfolio else None,
                symbol=symbol,
                trade_type=trade_type,
                amount=amount,
                price_eur=price,
                total_eur=total,
                fee_eur=fee,
                strategy=strategy,
                notes=notes,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(trade)
    
    def get_trade_history(self, symbol: Optional[str] = None, days: int = 30) -> List[Dict]:
        """Récupère l'historique des trades"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.get_session() as session:
            query = session.query(Trade).filter(
                Trade.timestamp >= cutoff
            )
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            
            trades = query.order_by(Trade.timestamp.desc()).all()
            
            return [
                {
                    'symbol': t.symbol,
                    'trade_type': t.trade_type,
                    'amount': t.amount,
                    'price_eur': t.price_eur,
                    'total_eur': t.total_eur,
                    'fee_eur': t.fee_eur,
                    'strategy': t.strategy,
                    'timestamp': t.timestamp
                }
                for t in trades
            ]
    
    # ========== BACKTESTING ==========
    
    def save_backtest_result(self, result: Dict):
        """Sauvegarde un résultat de backtest"""
        with self.get_session() as session:
            record = BacktestResult(
                strategy_name=result['strategy_name'],
                symbol=result['symbol'],
                start_date=result['start_date'],
                end_date=result['end_date'],
                initial_capital=result['initial_capital'],
                final_capital=result['final_capital'],
                total_return=result['total_return'],
                total_return_pct=result['total_return_pct'],
                sharpe_ratio=result.get('sharpe_ratio'),
                max_drawdown=result.get('max_drawdown'),
                win_rate=result.get('win_rate'),
                total_trades=result.get('total_trades', 0),
                winning_trades=result.get('winning_trades', 0),
                losing_trades=result.get('losing_trades', 0),
                avg_win=result.get('avg_win'),
                avg_loss=result.get('avg_loss'),
                profit_factor=result.get('profit_factor'),
                parameters=result.get('parameters', {}),
                trades_data=result.get('trades_data', []),
                equity_curve=result.get('equity_curve', [])
            )
            session.add(record)
    
    def get_backtest_results(self, strategy_name: Optional[str] = None, 
                            symbol: Optional[str] = None) -> List[Dict]:
        """Récupère les résultats de backtests"""
        with self.get_session() as session:
            query = session.query(BacktestResult)
            
            if strategy_name:
                query = query.filter(BacktestResult.strategy_name == strategy_name)
            
            if symbol:
                query = query.filter(BacktestResult.symbol == symbol)
            
            results = query.order_by(BacktestResult.created_at.desc()).all()
            
            return [
                {
                    'strategy_name': r.strategy_name,
                    'symbol': r.symbol,
                    'start_date': r.start_date,
                    'end_date': r.end_date,
                    'total_return_pct': r.total_return_pct,
                    'sharpe_ratio': r.sharpe_ratio,
                    'max_drawdown': r.max_drawdown,
                    'win_rate': r.win_rate,
                    'total_trades': r.total_trades
                }
                for r in results
            ]
    
    # ========== SYSTEM STATS ==========
    
    def save_system_stats(self, stats: Dict):
        """Sauvegarde les statistiques système"""
        with self.get_session() as session:
            record = SystemStats(
                checks_count=stats.get('checks_count', 0),
                alerts_sent=stats.get('alerts_sent', 0),
                predictions_made=stats.get('predictions_made', 0),
                predictions_correct=stats.get('predictions_correct', 0),
                errors_count=stats.get('errors_count', 0),
                uptime_seconds=stats.get('uptime_seconds', 0),
                last_check=stats.get('last_check'),
                timestamp=datetime.now(timezone.utc)
            )
            session.add(record)
    
    def get_latest_stats(self) -> Optional[Dict]:
        """Récupère les dernières statistiques"""
        with self.get_session() as session:
            record = session.query(SystemStats).order_by(
                SystemStats.timestamp.desc()
            ).first()
            
            if not record:
                return None
            
            return {
                'checks_count': record.checks_count,
                'alerts_sent': record.alerts_sent,
                'predictions_made': record.predictions_made,
                'predictions_correct': record.predictions_correct,
                'errors_count': record.errors_count,
                'uptime_seconds': record.uptime_seconds,
                'last_check': record.last_check
            }
