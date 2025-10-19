"""
Portfolio Service - Gestion du portfolio utilisateur
"""

from typing import Dict, List, Optional

from core.models import Portfolio, Position


class PortfolioService:
    """Service de gestion du portfolio"""
    
    def __init__(self):
        self.portfolio: Optional[Portfolio] = None
    
    def create_portfolio(self, initial_investment: float) -> Portfolio:
        """Crée un nouveau portfolio"""
        self.portfolio = Portfolio(total_investment_eur=initial_investment)
        return self.portfolio
    
    def add_position(self, symbol: str, amount: float, entry_price_eur: float) -> Position:
        """Ajoute une position au portfolio"""
        if not self.portfolio:
            self.create_portfolio(0.0)
        
        position = Position(
            symbol=symbol,
            amount=amount,
            entry_price_eur=entry_price_eur,
            current_price_eur=entry_price_eur,
            investment_eur=amount * entry_price_eur
        )
        
        self.portfolio.add_position(position)
        
        return position
    
    def update_prices(self, prices: Dict[str, float]):
        """Met à jour les prix des positions"""
        if not self.portfolio:
            return
        
        for symbol, current_price in prices.items():
            if symbol in self.portfolio.positions:
                self.portfolio.positions[symbol].update_values(current_price)
        
        self.portfolio.recalculate()
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Récupère une position"""
        if not self.portfolio:
            return None
        return self.portfolio.positions.get(symbol)
    
    def remove_position(self, symbol: str):
        """Supprime une position"""
        if not self.portfolio or symbol not in self.portfolio.positions:
            return
        
        del self.portfolio.positions[symbol]
        self.portfolio.recalculate()
    
    def get_summary(self) -> Dict:
        """Retourne un résumé du portfolio"""
        if not self.portfolio:
            return {
                "total_value": 0.0,
                "total_gain_loss": 0.0,
                "total_gain_loss_pct": 0.0,
                "positions_count": 0
            }
        
        return {
            "total_value": self.portfolio.total_value_eur,
            "total_gain_loss": self.portfolio.total_gain_loss_eur,
            "total_gain_loss_pct": self.portfolio.total_gain_loss_pct,
            "positions_count": len(self.portfolio.positions),
            "investment": self.portfolio.total_investment_eur
        }
    
    def get_best_performers(self, limit: int = 3) -> List[Position]:
        """Retourne les meilleures positions"""
        if not self.portfolio:
            return []
        
        positions = list(self.portfolio.positions.values())
        return sorted(positions, key=lambda p: p.gain_loss_pct, reverse=True)[:limit]
    
    def get_worst_performers(self, limit: int = 3) -> List[Position]:
        """Retourne les pires positions"""
        if not self.portfolio:
            return []
        
        positions = list(self.portfolio.positions.values())
        return sorted(positions, key=lambda p: p.gain_loss_pct)[:limit]
    
    def simulate_purchase(self, symbol: str, investment_eur: float, 
                         current_price_eur: float) -> Dict:
        """Simule un achat"""
        amount = investment_eur / current_price_eur
        
        return {
            "symbol": symbol,
            "investment_eur": investment_eur,
            "amount": amount,
            "entry_price": current_price_eur,
            "potential_5pct": investment_eur * 1.05,
            "potential_10pct": investment_eur * 1.10,
            "potential_20pct": investment_eur * 1.20
        }
