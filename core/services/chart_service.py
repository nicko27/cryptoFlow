"""
Chart Service - Génération de graphiques pour Telegram
"""

import matplotlib
matplotlib.use('Agg')  # Backend non-interactif
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Optional
from io import BytesIO
from core.models import CryptoPrice, MarketData


class ChartService:
    """Service de génération de graphiques"""
    
    def __init__(self):
        plt.style.use('dark_background')
    
    def generate_price_chart(self, symbol: str, prices: List[CryptoPrice], 
                            show_levels: bool = True, 
                            price_levels: dict = None) -> BytesIO:
        """Génère un graphique de prix"""
        
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1e1e1e')
        ax.set_facecolor('#1e1e1e')
        
        if not prices:
            return None
        
        # Données
        timestamps = [p.timestamp for p in prices]
        price_values = [p.price_eur for p in prices]
        
        # Tracer prix
        ax.plot(timestamps, price_values, linewidth=2, color='#00d9ff', label='Prix')
        
        # Niveaux de prix
        if show_levels and price_levels:
            if "low" in price_levels:
                ax.axhline(y=price_levels["low"], color='#00ff00', 
                          linestyle='--', linewidth=2, alpha=0.7,
                          label=f'Support {price_levels["low"]}€')
            
            if "high" in price_levels:
                ax.axhline(y=price_levels["high"], color='#ff0000',
                          linestyle='--', linewidth=2, alpha=0.7,
                          label=f'Résistance {price_levels["high"]}€')
        
        # Prix actuel
        current_price = price_values[-1]
        ax.axhline(y=current_price, color='#ffff00', linestyle=':',
                  linewidth=1.5, alpha=0.8, label=f'Actuel {current_price:.2f}€')
        
        # Styling
        ax.set_xlabel('Temps', color='white', fontsize=12)
        ax.set_ylabel('Prix (€)', color='white', fontsize=12)
        ax.set_title(f'{symbol} - Évolution du prix', color='white', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.legend(loc='upper left', facecolor='#2b2b2b', 
                 edgecolor='white', labelcolor='white')
        ax.grid(True, alpha=0.2, color='gray', linestyle=':')
        ax.tick_params(colors='white')
        
        # Format dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        fig.autofmt_xdate()
        
        # Sauvegarder
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='#1e1e1e', 
                   edgecolor='none', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def generate_indicators_chart(self, market_data: MarketData) -> BytesIO:
        """Génère un graphique multi-indicateurs"""
        
        if not market_data.price_history:
            return None
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), 
                                            facecolor='#1e1e1e')
        
        timestamps = [p.timestamp for p in market_data.price_history]
        prices = [p.price_eur for p in market_data.price_history]
        
        # 1. Prix
        ax1.set_facecolor('#1e1e1e')
        ax1.plot(timestamps, prices, linewidth=2, color='#00d9ff', label='Prix')
        ax1.set_ylabel('Prix (€)', color='white')
        ax1.set_title(f'{market_data.symbol} - Analyse technique', 
                     color='white', fontsize=16, fontweight='bold')
        ax1.legend(loc='upper left', facecolor='#2b2b2b')
        ax1.grid(True, alpha=0.2, color='gray')
        ax1.tick_params(colors='white')
        
        # 2. RSI
        ax2.set_facecolor('#1e1e1e')
        rsi_values = [market_data.technical_indicators.rsi] * len(timestamps)
        ax2.plot(timestamps, rsi_values, linewidth=2, color='#ff9500', label='RSI')
        ax2.axhline(y=70, color='#ff0000', linestyle='--', alpha=0.5)
        ax2.axhline(y=30, color='#00ff00', linestyle='--', alpha=0.5)
        ax2.set_ylabel('RSI', color='white')
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left', facecolor='#2b2b2b')
        ax2.grid(True, alpha=0.2, color='gray')
        ax2.tick_params(colors='white')
        
        # 3. Volume
        ax3.set_facecolor('#1e1e1e')
        volumes = [p.volume_24h for p in market_data.price_history]
        ax3.bar(timestamps, volumes, color='#00d9ff', alpha=0.5, label='Volume')
        ax3.set_xlabel('Temps', color='white')
        ax3.set_ylabel('Volume 24h', color='white')
        ax3.legend(loc='upper left', facecolor='#2b2b2b')
        ax3.grid(True, alpha=0.2, color='gray')
        ax3.tick_params(colors='white')
        
        # Format dates
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        fig.autofmt_xdate()
        
        # Sauvegarder
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='#1e1e1e', 
                   edgecolor='none', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    def generate_comparison_chart(self, markets_data: dict) -> BytesIO:
        """Génère un graphique de comparaison"""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), 
                                       facecolor='#1e1e1e')
        
        symbols = list(markets_data.keys())
        
        # 1. Changement 24h
        ax1.set_facecolor('#1e1e1e')
        changes = [markets_data[s].current_price.change_24h for s in symbols]
        colors = ['#00ff00' if c > 0 else '#ff0000' for c in changes]
        ax1.barh(symbols, changes, color=colors, alpha=0.8)
        ax1.set_xlabel('Changement 24h (%)', color='white')
        ax1.set_title('Performance 24h', color='white', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.2, color='gray', axis='x')
        ax1.tick_params(colors='white')
        ax1.axvline(x=0, color='white', linestyle='-', linewidth=0.5)
        
        # 2. RSI
        ax2.set_facecolor('#1e1e1e')
        rsi_values = [markets_data[s].technical_indicators.rsi for s in symbols]
        colors = ['#00ff00' if r < 40 else '#ff0000' if r > 60 else '#ffff00' 
                 for r in rsi_values]
        ax2.barh(symbols, rsi_values, color=colors, alpha=0.8)
        ax2.set_xlabel('RSI', color='white')
        ax2.set_title('RSI Comparison', color='white', fontsize=14, fontweight='bold')
        ax2.set_xlim(0, 100)
        ax2.axvline(x=30, color='#00ff00', linestyle='--', alpha=0.5)
        ax2.axvline(x=70, color='#ff0000', linestyle='--', alpha=0.5)
        ax2.grid(True, alpha=0.2, color='gray', axis='x')
        ax2.tick_params(colors='white')
        
        # Sauvegarder
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', facecolor='#1e1e1e', 
                   edgecolor='none', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
