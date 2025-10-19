"""
Module de graphiques avancés - Tendance 7 jours
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from datetime import datetime, timedelta, timezone, timezone
from typing import List, Dict, Optional
import io
from core.models import CryptoPrice, MarketData


class ChartGenerator:
    """Générateur de graphiques avancés"""
    
    def __init__(self, dark_mode: bool = True):
        self.dark_mode = dark_mode
        self.bg_color = '#2b2b2b' if dark_mode else 'white'
        self.text_color = 'white' if dark_mode else 'black'
    
    def create_7day_trend_chart(self, 
                                symbol: str,
                                price_history: List[CryptoPrice],
                                show_ma: bool = True,
                                show_support_resistance: bool = True) -> io.BytesIO:
        """
        Crée un graphique de tendance sur 7 jours
        
        Args:
            symbol: Symbole crypto
            price_history: Historique des prix (7 jours minimum)
            show_ma: Afficher moyennes mobiles
            show_support_resistance: Afficher support/résistance
        
        Returns:
            BytesIO contenant l'image PNG
        """
        fig = Figure(figsize=(14, 8), facecolor=self.bg_color)
        
        # 2 subplots: Prix + Volume
        ax1 = fig.add_subplot(2, 1, 1, facecolor=self.bg_color)
        ax2 = fig.add_subplot(2, 1, 2, facecolor=self.bg_color)
        
        # Filtrer 7 derniers jours
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_prices = [p for p in price_history if p.timestamp >= cutoff]
        
        if not recent_prices:
            return None
        
        timestamps = [p.timestamp for p in recent_prices]
        prices = [p.price_eur for p in recent_prices]
        volumes = [p.volume_24h for p in recent_prices]
        
        # === GRAPHIQUE PRIX ===
        ax1.plot(timestamps, prices, linewidth=2, color='#00BCD4', 
                label='Prix', marker='o', markersize=2, alpha=0.8)
        
        # Moyennes mobiles
        if show_ma and len(prices) >= 20:
            ma20 = self._moving_average(prices, 20)
            ma50 = self._moving_average(prices, 50) if len(prices) >= 50 else None
            
            ax1.plot(timestamps[-len(ma20):], ma20, '--', 
                    color='#FFC107', linewidth=1.5, label='MA20', alpha=0.7)
            
            if ma50:
                ax1.plot(timestamps[-len(ma50):], ma50, '--',
                        color='#FF5722', linewidth=1.5, label='MA50', alpha=0.7)
        
        # Support/Résistance
        if show_support_resistance:
            support = self._find_support(prices)
            resistance = self._find_resistance(prices)
            
            ax1.axhline(y=support, color='green', linestyle=':', 
                       linewidth=2, label=f'Support ({support:.0f}€)', alpha=0.6)
            ax1.axhline(y=resistance, color='red', linestyle=':', 
                       linewidth=2, label=f'Résistance ({resistance:.0f}€)', alpha=0.6)
        
        # Prix actuel
        current_price = prices[-1]
        ax1.axhline(y=current_price, color='white', linestyle='--', 
                   linewidth=1, alpha=0.5)
        ax1.text(timestamps[-1], current_price, f' {current_price:.2f}€', 
                color='white', va='center', fontweight='bold')
        
        # Styling prix
        ax1.set_ylabel('Prix (€)', color=self.text_color, fontsize=12)
        ax1.set_title(f'{symbol} - Tendance 7 jours', 
                     color=self.text_color, fontsize=16, fontweight='bold', pad=20)
        ax1.legend(loc='upper left', facecolor=self.bg_color, 
                  edgecolor=self.text_color, labelcolor=self.text_color)
        ax1.grid(True, alpha=0.3, color='gray')
        ax1.tick_params(colors=self.text_color)
        
        # === GRAPHIQUE VOLUME ===
        colors = ['green' if prices[i] >= prices[i-1] else 'red' 
                 for i in range(1, len(prices))]
        colors.insert(0, 'gray')
        
        ax2.bar(timestamps, volumes, color=colors, alpha=0.6, width=0.003)
        ax2.set_ylabel('Volume 24h', color=self.text_color, fontsize=12)
        ax2.set_xlabel('Date', color=self.text_color, fontsize=12)
        ax2.tick_params(colors=self.text_color)
        ax2.grid(True, alpha=0.3, color='gray', axis='y')
        
        # Format dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %Hh'))
        fig.autofmt_xdate()
        
        # Calculer statistiques
        change_7d = ((prices[-1] - prices[0]) / prices[0]) * 100
        high_7d = max(prices)
        low_7d = min(prices)
        
        # Texte stats
        stats_text = (f"7j: {change_7d:+.2f}% | "
                     f"Max: {high_7d:.2f}€ | "
                     f"Min: {low_7d:.2f}€")
        
        fig.text(0.5, 0.97, stats_text, ha='center', 
                color=self.text_color, fontsize=11, 
                bbox=dict(boxstyle='round', facecolor=self.bg_color, 
                         edgecolor=self.text_color, alpha=0.8))
        
        plt.tight_layout()
        
        # Sauvegarder en BytesIO
        buf = io.BytesIO()
        fig.savefig(buf, format='png', facecolor=self.bg_color, 
                   edgecolor='none', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def create_comparison_chart(self, 
                               symbols: List[str],
                               market_data: Dict[str, MarketData]) -> io.BytesIO:
        """
        Crée un graphique de comparaison multi-crypto
        
        Args:
            symbols: Liste des symboles
            market_data: Dict {symbol: MarketData}
        
        Returns:
            BytesIO contenant l'image PNG
        """
        fig = Figure(figsize=(12, 7), facecolor=self.bg_color)
        ax = fig.add_subplot(111, facecolor=self.bg_color)
        
        colors = ['#00BCD4', '#4CAF50', '#FF9800', '#9C27B0', '#F44336']
        
        for i, symbol in enumerate(symbols):
            if symbol not in market_data:
                continue
            
            data = market_data[symbol]
            if not data.price_history:
                continue
            
            # Normaliser à 100 pour comparaison
            prices = [p.price_eur for p in data.price_history]
            normalized = [(p / prices[0]) * 100 for p in prices]
            timestamps = [p.timestamp for p in data.price_history]
            
            ax.plot(timestamps, normalized, linewidth=2, 
                   color=colors[i % len(colors)], 
                   label=symbol, marker='o', markersize=2, alpha=0.8)
        
        ax.axhline(y=100, color='white', linestyle='--', 
                  linewidth=1, alpha=0.5, label='Base 100')
        
        ax.set_ylabel('Performance relative (base 100)', 
                     color=self.text_color, fontsize=12)
        ax.set_xlabel('Date', color=self.text_color, fontsize=12)
        ax.set_title('Comparaison Performance - 7 jours', 
                    color=self.text_color, fontsize=14, fontweight='bold')
        ax.legend(loc='best', facecolor=self.bg_color, 
                 edgecolor=self.text_color, labelcolor=self.text_color)
        ax.grid(True, alpha=0.3, color='gray')
        ax.tick_params(colors=self.text_color)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', facecolor=self.bg_color, 
                   edgecolor='none', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def _moving_average(self, prices: List[float], period: int) -> List[float]:
        """Calcule moyenne mobile"""
        if len(prices) < period:
            return []
        
        ma = []
        for i in range(period - 1, len(prices)):
            ma.append(sum(prices[i-period+1:i+1]) / period)
        
        return ma
    
    def _find_support(self, prices: List[float]) -> float:
        """Trouve support"""
        sorted_prices = sorted(prices)
        return sorted_prices[int(len(sorted_prices) * 0.1)]
    
    def _find_resistance(self, prices: List[float]) -> float:
        """Trouve résistance"""
        sorted_prices = sorted(prices)
        return sorted_prices[int(len(sorted_prices) * 0.9)]


# Test
if __name__ == "__main__":
    print("📊 Module de graphiques chargé")
    print("Utilisation: chart_gen = ChartGenerator()")
    print("  chart_gen.create_7day_trend_chart(symbol, price_history)")
