"""
Backtesting Engine - Test de stratégies sur données historiques
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta, timezone, timezone
from dataclasses import dataclass, field

from core.models import CryptoPrice, MarketData, TechnicalIndicators


@dataclass
class BacktestTrade:
    """Trade exécuté pendant le backtest"""
    timestamp: datetime
    symbol: str
    action: str  # 'BUY' ou 'SELL'
    price: float
    amount: float
    total: float
    fee: float = 0.0
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'price': self.price,
            'amount': self.amount,
            'total': self.total,
            'fee': self.fee,
            'reason': self.reason
        }


@dataclass
class BacktestResult:
    """Résultat d'un backtest"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    
    # Métriques de performance
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Stats de trading
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Données détaillées
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'trades_data': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve,
            'parameters': self.parameters
        }


class BacktestEngine:
    """Moteur de backtesting"""
    
    def __init__(self, initial_capital: float = 10000.0, fee_pct: float = 0.1):
        """
        Args:
            initial_capital: Capital initial
            fee_pct: Frais de transaction en %
        """
        self.initial_capital = initial_capital
        self.fee_pct = fee_pct
        
        # État du backtest
        self.cash = initial_capital
        self.position_size = 0.0  # Quantité de crypto détenue
        self.position_value = 0.0
        self.equity = initial_capital
        
        # Historique
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Dict] = []
        
    def reset(self):
        """Réinitialise l'état du backtest"""
        self.cash = self.initial_capital
        self.position_size = 0.0
        self.position_value = 0.0
        self.equity = self.initial_capital
        self.trades = []
        self.equity_curve = []
    
    def buy(self, price: float, amount: float, timestamp: datetime, reason: str = ""):
        """Exécute un achat"""
        total = amount * price
        fee = total * (self.fee_pct / 100)
        cost = total + fee
        
        if cost > self.cash:
            # Ajuster l'amount pour utiliser tout le cash disponible
            amount = (self.cash / (1 + self.fee_pct / 100)) / price
            total = amount * price
            fee = total * (self.fee_pct / 100)
            cost = total + fee
        
        if cost <= 0 or amount <= 0:
            return
        
        self.cash -= cost
        self.position_size += amount
        
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol="BTC",  # Simplifié
            action="BUY",
            price=price,
            amount=amount,
            total=total,
            fee=fee,
            reason=reason
        )
        self.trades.append(trade)
    
    def sell(self, price: float, amount: Optional[float] = None, 
            timestamp: Optional[datetime] = None, reason: str = ""):
        """Exécute une vente"""
        if self.position_size <= 0:
            return
        
        # Si amount non spécifié, vendre tout
        if amount is None or amount > self.position_size:
            amount = self.position_size
        
        total = amount * price
        fee = total * (self.fee_pct / 100)
        proceeds = total - fee
        
        self.cash += proceeds
        self.position_size -= amount
        
        trade = BacktestTrade(
            timestamp=timestamp or datetime.now(timezone.utc),
            symbol="BTC",
            action="SELL",
            price=price,
            amount=amount,
            total=total,
            fee=fee,
            reason=reason
        )
        self.trades.append(trade)
    
    def update_equity(self, current_price: float, timestamp: datetime):
        """Met à jour l'équité"""
        self.position_value = self.position_size * current_price
        self.equity = self.cash + self.position_value
        
        self.equity_curve.append({
            'timestamp': timestamp.isoformat(),
            'equity': self.equity,
            'cash': self.cash,
            'position_value': self.position_value
        })
    
    def run_backtest(self, 
                    prices: List[CryptoPrice],
                    strategy: Callable,
                    strategy_name: str,
                    symbol: str,
                    parameters: Dict = None) -> BacktestResult:
        """
        Exécute un backtest
        
        Args:
            prices: Historique des prix
            strategy: Fonction de stratégie qui retourne 'BUY', 'SELL' ou 'HOLD'
            strategy_name: Nom de la stratégie
            symbol: Symbole de la crypto
            parameters: Paramètres de la stratégie
        
        Returns:
            BacktestResult
        """
        self.reset()
        
        if not prices or len(prices) < 2:
            return self._create_empty_result(strategy_name, symbol)
        
        start_date = prices[0].timestamp
        end_date = prices[-1].timestamp
        
        # Simuler le trading
        for i, price_data in enumerate(prices):
            current_price = price_data.price_eur
            timestamp = price_data.timestamp
            
            # Créer MarketData simplifié pour la stratégie
            market_data = self._create_market_data_from_history(prices[:i+1], symbol)
            
            # Obtenir le signal de la stratégie
            try:
                signal = strategy(market_data, parameters or {})
            except Exception as e:
                print(f"⚠️ Erreur stratégie: {e}")
                signal = 'HOLD'
            
            # Exécuter le signal
            if signal == 'BUY' and self.cash > 0:
                # Acheter avec tout le cash
                self.buy(current_price, self.cash / current_price, timestamp, 
                        reason=f"Signal: {signal}")
            
            elif signal == 'SELL' and self.position_size > 0:
                # Vendre toute la position
                self.sell(current_price, self.position_size, timestamp,
                         reason=f"Signal: {signal}")
            
            # Mettre à jour l'équité
            self.update_equity(current_price, timestamp)
        
        # Vendre toute position restante à la fin
        if self.position_size > 0:
            final_price = prices[-1].price_eur
            self.sell(final_price, self.position_size, prices[-1].timestamp,
                     reason="Fin du backtest")
            self.update_equity(final_price, prices[-1].timestamp)
        
        # Calculer les métriques
        return self._calculate_metrics(
            strategy_name, symbol, start_date, end_date, parameters or {}
        )
    
    def _create_market_data_from_history(self, prices: List[CryptoPrice], 
                                        symbol: str) -> MarketData:
        """Crée un MarketData à partir de l'historique"""
        if not prices:
            return None
        
        current_price = prices[-1]
        
        # Calculer indicateurs techniques simplifiés
        price_values = [p.price_eur for p in prices]
        
        rsi = self._calculate_rsi(price_values) if len(price_values) >= 14 else 50
        ma20 = np.mean(price_values[-20:]) if len(price_values) >= 20 else price_values[-1]
        ma50 = np.mean(price_values[-50:]) if len(price_values) >= 50 else price_values[-1]
        
        ti = TechnicalIndicators(
            rsi=rsi,
            ma20=ma20,
            ma50=ma50
        )
        
        return MarketData(
            symbol=symbol,
            current_price=current_price,
            technical_indicators=ti,
            price_history=prices
        )
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcule le RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_metrics(self, strategy_name: str, symbol: str,
                          start_date: datetime, end_date: datetime,
                          parameters: Dict) -> BacktestResult:
        """Calcule toutes les métriques du backtest"""
        
        final_capital = self.equity
        total_return = final_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Sharpe ratio
        returns = self._calculate_returns()
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        
        # Max drawdown
        max_dd, max_dd_pct = self._calculate_max_drawdown()
        
        # Stats de trading
        winning_trades = [t for t in self.trades 
                         if t.action == 'SELL' and self._is_winning_trade(t)]
        losing_trades = [t for t in self.trades 
                        if t.action == 'SELL' and not self._is_winning_trade(t)]
        
        total_trades = len([t for t in self.trades if t.action == 'SELL'])
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        
        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = np.mean([self._calculate_trade_pnl(t) for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([self._calculate_trade_pnl(t) for t in losing_trades]) if losing_trades else 0
        
        total_wins = sum([self._calculate_trade_pnl(t) for t in winning_trades])
        total_losses = abs(sum([self._calculate_trade_pnl(t) for t in losing_trades]))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            total_trades=total_trades,
            winning_trades=num_wins,
            losing_trades=num_losses,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=self.equity_curve,
            parameters=parameters
        )
    
    def _calculate_returns(self) -> List[float]:
        """Calcule les rendements périodiques"""
        if len(self.equity_curve) < 2:
            return [0.0]
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1]['equity']
            curr_equity = self.equity_curve[i]['equity']
            
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        return returns if returns else [0.0]
    
    def _calculate_sharpe_ratio(self, returns: List[float], 
                               risk_free_rate: float = 0.02) -> float:
        """Calcule le Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate / 252 for r in returns]  # 252 jours de trading
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: List[float],
                                 risk_free_rate: float = 0.02) -> float:
        """Calcule le Sortino ratio (uniquement downside risk)"""
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate / 252 for r in returns]
        downside_returns = [r for r in excess_returns if r < 0]
        
        if not downside_returns or np.std(downside_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
    
    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """Calcule le maximum drawdown"""
        if not self.equity_curve:
            return 0.0, 0.0
        
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0.0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0
        
        return max_dd, max_dd_pct
    
    def _is_winning_trade(self, sell_trade: BacktestTrade) -> bool:
        """Détermine si un trade est gagnant"""
        # Trouver le dernier achat avant cette vente
        buy_trades = [t for t in self.trades 
                     if t.action == 'BUY' and t.timestamp < sell_trade.timestamp]
        
        if not buy_trades:
            return False
        
        last_buy = buy_trades[-1]
        
        return sell_trade.price > last_buy.price
    
    def _calculate_trade_pnl(self, sell_trade: BacktestTrade) -> float:
        """Calcule le P&L d'un trade"""
        # Trouver le dernier achat
        buy_trades = [t for t in self.trades 
                     if t.action == 'BUY' and t.timestamp < sell_trade.timestamp]
        
        if not buy_trades:
            return 0.0
        
        last_buy = buy_trades[-1]
        
        buy_cost = last_buy.total + last_buy.fee
        sell_proceeds = sell_trade.total - sell_trade.fee
        
        return sell_proceeds - buy_cost
    
    def _create_empty_result(self, strategy_name: str, symbol: str) -> BacktestResult:
        """Crée un résultat vide pour les cas d'erreur"""
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0.0,
            total_return_pct=0.0
        )


# Exemple de stratégie pour le backtesting
def rsi_strategy(market_data: MarketData, params: Dict) -> str:
    """
    Stratégie simple basée sur le RSI
    
    Params:
        oversold: Seuil de survente (défaut: 30)
        overbought: Seuil de surachat (défaut: 70)
    """
    if not market_data:
        return 'HOLD'
    
    rsi = market_data.technical_indicators.rsi
    oversold = params.get('oversold', 30)
    overbought = params.get('overbought', 70)
    
    if rsi < oversold:
        return 'BUY'
    elif rsi > overbought:
        return 'SELL'
    
    return 'HOLD'


def ma_crossover_strategy(market_data: MarketData, params: Dict) -> str:
    """
    Stratégie de croisement de moyennes mobiles
    
    Params:
        fast_period: Période MA rapide (défaut: 20)
        slow_period: Période MA lente (défaut: 50)
    """
    if not market_data or len(market_data.price_history) < 2:
        return 'HOLD'
    
    ti = market_data.technical_indicators
    current_price = market_data.current_price.price_eur
    
    # Golden cross : MA rapide croise MA lente à la hausse
    if ti.ma20 > ti.ma50 and current_price > ti.ma20:
        return 'BUY'
    
    # Death cross : MA rapide croise MA lente à la baisse
    elif ti.ma20 < ti.ma50 and current_price < ti.ma20:
        return 'SELL'
    
    return 'HOLD'
