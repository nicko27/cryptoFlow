"""
Portfolio & Risk Management - Gestion complète du portfolio et du risque
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from core.models import CryptoPrice, MarketData


@dataclass
class Position:
    """Position sur une crypto"""
    symbol: str
    amount: float  # Quantité détenue
    entry_price: float
    current_price: float
    investment: float
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    weight: float = 0.0  # Poids dans le portfolio
    entry_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update(self, current_price: float):
        """Met à jour la position avec le prix actuel"""
        self.current_price = current_price
        self.current_value = self.amount * current_price
        self.unrealized_pnl = self.current_value - self.investment
        
        if self.investment > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.investment) * 100
        
        self.last_updated = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'amount': self.amount,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'investment': self.investment,
            'current_value': self.current_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'weight': self.weight,
            'entry_date': self.entry_date.isoformat()
        }


class PortfolioManager:
    """Gestionnaire de portfolio"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict] = []
        
        # Métriques de performance
        self.total_realized_pnl = 0.0
        self.total_fees_paid = 0.0
    
    def add_position(self, symbol: str, amount: float, entry_price: float):
        """Ajoute ou augmente une position"""
        investment = amount * entry_price
        
        if investment > self.cash:
            print(f"⚠️ Pas assez de cash ({self.cash:.2f} < {investment:.2f})")
            return False
        
        if symbol in self.positions:
            # Augmenter position existante (average down/up)
            pos = self.positions[symbol]
            total_amount = pos.amount + amount
            total_investment = pos.investment + investment
            new_avg_price = total_investment / total_amount
            
            pos.amount = total_amount
            pos.entry_price = new_avg_price
            pos.investment = total_investment
            pos.update(entry_price)
        else:
            # Nouvelle position
            position = Position(
                symbol=symbol,
                amount=amount,
                entry_price=entry_price,
                current_price=entry_price,
                investment=investment
            )
            position.update(entry_price)
            self.positions[symbol] = position
        
        self.cash -= investment
        self._recalculate_weights()
        
        return True
    
    def close_position(self, symbol: str, exit_price: float, 
                      amount: Optional[float] = None) -> Tuple[bool, float]:
        """
        Ferme une position (totalement ou partiellement)
        
        Returns:
            (success, realized_pnl)
        """
        if symbol not in self.positions:
            return False, 0.0
        
        pos = self.positions[symbol]
        
        # Montant à vendre
        sell_amount = amount if amount and amount <= pos.amount else pos.amount
        
        # Calcul du P&L réalisé
        sell_value = sell_amount * exit_price
        cost_basis = (pos.investment / pos.amount) * sell_amount
        realized_pnl = sell_value - cost_basis
        
        self.cash += sell_value
        self.total_realized_pnl += realized_pnl
        
        # Enregistrer la position fermée
        self.closed_positions.append({
            'symbol': symbol,
            'amount': sell_amount,
            'entry_price': pos.entry_price,
            'exit_price': exit_price,
            'realized_pnl': realized_pnl,
            'realized_pnl_pct': (realized_pnl / cost_basis) * 100,
            'entry_date': pos.entry_date,
            'exit_date': datetime.now(timezone.utc),
            'duration_days': (datetime.now(timezone.utc) - pos.entry_date).days
        })
        
        # Mettre à jour ou supprimer la position
        if sell_amount >= pos.amount:
            del self.positions[symbol]
        else:
            pos.amount -= sell_amount
            pos.investment -= cost_basis
            pos.update(exit_price)
        
        self._recalculate_weights()
        
        return True, realized_pnl
    
    def update_positions(self, market_prices: Dict[str, float]):
        """Met à jour toutes les positions avec les prix actuels"""
        for symbol, price in market_prices.items():
            if symbol in self.positions:
                self.positions[symbol].update(price)
        
        self._recalculate_weights()
    
    def _recalculate_weights(self):
        """Recalcule les poids de chaque position"""
        total_value = self.get_total_portfolio_value()
        
        for pos in self.positions.values():
            pos.weight = (pos.current_value / total_value * 100) if total_value > 0 else 0
    
    def get_total_portfolio_value(self) -> float:
        """Retourne la valeur totale du portfolio"""
        positions_value = sum(pos.current_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_total_unrealized_pnl(self) -> float:
        """Retourne le P&L non réalisé total"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_portfolio_return(self) -> Tuple[float, float]:
        """
        Retourne le rendement total du portfolio
        
        Returns:
            (return_amount, return_pct)
        """
        current_value = self.get_total_portfolio_value()
        total_return = current_value - self.initial_capital
        return_pct = (total_return / self.initial_capital) * 100
        
        return total_return, return_pct
    
    def get_portfolio_summary(self) -> Dict:
        """Retourne un résumé complet du portfolio"""
        total_value = self.get_total_portfolio_value()
        total_return, return_pct = self.get_portfolio_return()
        unrealized_pnl = self.get_total_unrealized_pnl()
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'positions_value': total_value - self.cash,
            'initial_capital': self.initial_capital,
            'total_return': total_return,
            'total_return_pct': return_pct,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': self.total_realized_pnl,
            'total_fees': self.total_fees_paid,
            'num_positions': len(self.positions),
            'positions': [pos.to_dict() for pos in self.positions.values()],
            'closed_positions_count': len(self.closed_positions)
        }


class RiskManager:
    """Gestionnaire de risque"""
    
    def __init__(self, max_position_size_pct: float = 20.0,
                max_portfolio_risk_pct: float = 2.0,
                max_drawdown_pct: float = 15.0):
        """
        Args:
            max_position_size_pct: Taille max d'une position (% du portfolio)
            max_portfolio_risk_pct: Risque max par trade (% du portfolio)
            max_drawdown_pct: Drawdown maximum acceptable
        """
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_drawdown_pct = max_drawdown_pct
        
        # Historique pour calcul de métriques
        self.equity_history: List[Dict] = []
    
    def calculate_position_size(self, portfolio_value: float, 
                               entry_price: float,
                               stop_loss_price: float) -> float:
        """
        Calcule la taille de position optimale
        
        Args:
            portfolio_value: Valeur totale du portfolio
            entry_price: Prix d'entrée
            stop_loss_price: Prix de stop loss
        
        Returns:
            Montant à investir en EUR
        """
        # Position size basée sur le risque
        risk_per_unit = abs(entry_price - stop_loss_price)
        risk_amount = portfolio_value * (self.max_portfolio_risk_pct / 100)
        
        if risk_per_unit > 0:
            max_units = risk_amount / risk_per_unit
            position_value = max_units * entry_price
        else:
            position_value = 0
        
        # Limiter à la taille max de position
        max_position_value = portfolio_value * (self.max_position_size_pct / 100)
        position_value = min(position_value, max_position_value)
        
        return position_value
    
    def calculate_stop_loss(self, entry_price: float, 
                           risk_pct: float = 5.0,
                           use_atr: bool = False,
                           atr_value: float = 0.0) -> float:
        """
        Calcule le stop loss
        
        Args:
            entry_price: Prix d'entrée
            risk_pct: Pourcentage de risque acceptable
            use_atr: Utiliser l'ATR pour le stop loss
            atr_value: Valeur de l'ATR
        
        Returns:
            Prix du stop loss
        """
        if use_atr and atr_value > 0:
            # Stop loss basé sur ATR (Average True Range)
            return entry_price - (2 * atr_value)
        else:
            # Stop loss basé sur pourcentage
            return entry_price * (1 - risk_pct / 100)
    
    def calculate_take_profit(self, entry_price: float,
                             stop_loss_price: float,
                             risk_reward_ratio: float = 2.0) -> float:
        """
        Calcule le take profit basé sur le risk/reward ratio
        
        Args:
            entry_price: Prix d'entrée
            stop_loss_price: Prix du stop loss
            risk_reward_ratio: Ratio risk/reward (défaut: 2.0)
        
        Returns:
            Prix du take profit
        """
        risk = entry_price - stop_loss_price
        reward = risk * risk_reward_ratio
        
        return entry_price + reward
    
    def check_drawdown(self, current_equity: float, peak_equity: float) -> Dict:
        """
        Vérifie le drawdown
        
        Returns:
            Dict avec drawdown info et alerte si nécessaire
        """
        if peak_equity <= 0:
            return {'drawdown_pct': 0, 'alert': False}
        
        drawdown = peak_equity - current_equity
        drawdown_pct = (drawdown / peak_equity) * 100
        
        alert = drawdown_pct > self.max_drawdown_pct
        
        return {
            'drawdown': drawdown,
            'drawdown_pct': drawdown_pct,
            'peak_equity': peak_equity,
            'current_equity': current_equity,
            'alert': alert,
            'message': f"⚠️ Drawdown de {drawdown_pct:.2f}% (max: {self.max_drawdown_pct}%)" if alert else ""
        }
    
    def calculate_sharpe_ratio(self, returns: List[float], 
                              risk_free_rate: float = 0.02) -> float:
        """
        Calcule le Sharpe ratio
        
        Args:
            returns: Liste des rendements périodiques
            risk_free_rate: Taux sans risque annuel
        
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        excess_returns = [r - risk_free_rate / 252 for r in returns]
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Tuple[float, float]:
        """
        Calcule le maximum drawdown
        
        Returns:
            (max_drawdown_value, max_drawdown_pct)
        """
        if not equity_curve:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0
        
        return max_dd, max_dd_pct
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        Calcule la Value at Risk (VaR)
        
        Args:
            returns: Liste des rendements
            confidence: Niveau de confiance (0.95 = 95%)
        
        Returns:
            VaR (perte maximale attendue avec X% de confiance)
        """
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        
        return abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
    
    def calculate_kelly_criterion(self, win_rate: float, 
                                  avg_win: float, 
                                  avg_loss: float) -> float:
        """
        Calcule le Kelly Criterion pour la taille de position optimale
        
        Args:
            win_rate: Taux de victoire (0-1)
            avg_win: Gain moyen
            avg_loss: Perte moyenne
        
        Returns:
            Fraction du capital à risquer (0-1)
        """
        if avg_loss == 0 or win_rate == 0:
            return 0.0
        
        loss_rate = 1 - win_rate
        win_loss_ratio = avg_win / abs(avg_loss)
        
        kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # Limiter Kelly à 25% max (half-Kelly pour être conservateur)
        return max(0, min(kelly * 0.5, 0.25))
    
    def diversification_check(self, positions: Dict[str, Position]) -> Dict:
        """
        Vérifie la diversification du portfolio
        
        Returns:
            Dict avec métriques de diversification
        """
        if not positions:
            return {
                'concentration_risk': 'LOW',
                'largest_position_pct': 0,
                'herfindahl_index': 0
            }
        
        # Trouver la plus grosse position
        weights = [pos.weight for pos in positions.values()]
        largest_weight = max(weights)
        
        # Calcul de l'indice de Herfindahl (concentration)
        # HHI = sum(weight^2), 0-10000
        # < 1500: faible concentration, > 2500: forte concentration
        hhi = sum(w**2 for w in weights)
        
        # Évaluation du risque de concentration
        if largest_weight > 40:
            risk = 'HIGH'
        elif largest_weight > 25:
            risk = 'MEDIUM'
        else:
            risk = 'LOW'
        
        return {
            'concentration_risk': risk,
            'largest_position_pct': largest_weight,
            'num_positions': len(positions),
            'herfindahl_index': hhi,
            'message': self._get_diversification_message(risk, largest_weight)
        }
    
    def _get_diversification_message(self, risk: str, largest_pct: float) -> str:
        """Message selon le risque de concentration"""
        if risk == 'HIGH':
            return f"⚠️ Forte concentration: {largest_pct:.1f}% dans une seule position"
        elif risk == 'MEDIUM':
            return f"⚡ Concentration modérée: {largest_pct:.1f}% dans une position"
        else:
            return f"✅ Bonne diversification (max {largest_pct:.1f}%)"
    
    def calculate_correlation(self, prices1: List[float], 
                            prices2: List[float]) -> float:
        """
        Calcule la corrélation entre deux actifs
        
        Returns:
            Coefficient de corrélation (-1 à 1)
        """
        if len(prices1) != len(prices2) or len(prices1) < 2:
            return 0.0
        
        return np.corrcoef(prices1, prices2)[0, 1]
