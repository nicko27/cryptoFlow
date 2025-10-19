"""
Advanced Charts - Graphiques avancés avec chandeliers, volumes, multi-timeframes
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import mplfinance as mpf
import pandas as pd
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import io

from core.models import CryptoPrice, MarketData, TechnicalIndicators


class AdvancedCharts:
    """Génération de graphiques avancés"""
    
    def __init__(self, style='dark'):
        self.style = style
        self._setup_style()
    
    def _setup_style(self):
        """Configure le style des graphiques"""
        if self.style == 'dark':
            plt.style.use('dark_background')
            self.colors = {
                'up': '#26A69A',
                'down': '#EF5350',
                'volume': '#4FC3F7',
                'ma': ['#FFA726', '#AB47BC', '#42A5F5'],
                'background': '#1E1E1E',
                'grid': '#424242'
            }
        else:
            self.colors = {
                'up': '#4CAF50',
                'down': '#F44336',
                'volume': '#2196F3',
                'ma': ['#FF9800', '#9C27B0', '#2196F3'],
                'background': '#FFFFFF',
                'grid': '#E0E0E0'
            }
    
    def create_candlestick_chart(self, prices: List[CryptoPrice], 
                                 symbol: str,
                                 indicators: Optional[TechnicalIndicators] = None,
                                 show_volume: bool = True,
                                 show_ma: bool = True,
                                 figsize: Tuple[int, int] = (12, 8)) -> Figure:
        """
        Crée un graphique en chandeliers
        
        Args:
            prices: Liste de prix
            symbol: Symbole de la crypto
            indicators: Indicateurs techniques à afficher
            show_volume: Afficher les volumes
            show_ma: Afficher les moyennes mobiles
            figsize: Taille de la figure
        
        Returns:
            Figure matplotlib
        """
        # Convertir en DataFrame
        df = self._prices_to_dataframe(prices)
        
        if df.empty:
            return self._create_empty_figure(figsize)
        
        # Créer figure avec subplots
        if show_volume:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, 
                                          gridspec_kw={'height_ratios': [3, 1]},
                                          facecolor=self.colors['background'])
        else:
            fig, ax1 = plt.subplots(figsize=figsize, facecolor=self.colors['background'])
            ax2 = None
        
        # Chandeliers
        self._plot_candlesticks(ax1, df)
        
        # Moyennes mobiles
        if show_ma and indicators:
            self._plot_moving_averages(ax1, df, indicators)
        
        # Bandes de Bollinger
        if indicators and indicators.bollinger_upper > 0:
            self._plot_bollinger_bands(ax1, df, indicators)
        
        # Support/Résistance
        if indicators and indicators.support > 0:
            self._plot_support_resistance(ax1, indicators)
        
        # Volumes
        if show_volume and ax2:
            self._plot_volume(ax2, df)
        
        # Styling
        ax1.set_title(f'{symbol} - Graphique en chandeliers', 
                     fontsize=14, fontweight='bold', color='white')
        ax1.grid(True, alpha=0.3, color=self.colors['grid'])
        ax1.legend(loc='upper left', facecolor=self.colors['background'])
        
        if ax2:
            ax2.grid(True, alpha=0.3, color=self.colors['grid'])
        
        plt.tight_layout()
        return fig
    
    def create_technical_indicators_chart(self, prices: List[CryptoPrice],
                                         symbol: str,
                                         indicators: TechnicalIndicators,
                                         figsize: Tuple[int, int] = (12, 10)) -> Figure:
        """
        Crée un graphique avec tous les indicateurs techniques
        
        Returns:
            Figure avec prix + RSI + MACD + Stochastique
        """
        df = self._prices_to_dataframe(prices)
        
        if df.empty:
            return self._create_empty_figure(figsize)
        
        # 4 subplots: Prix, RSI, MACD, Stochastique
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=figsize,
                                                 gridspec_kw={'height_ratios': [3, 1, 1, 1]},
                                                 facecolor=self.colors['background'])
        
        # 1. Prix avec chandeliers
        self._plot_candlesticks(ax1, df)
        if indicators.ma20 > 0:
            ax1.axhline(y=indicators.ma20, color=self.colors['ma'][0], 
                       linestyle='--', label='MA20', alpha=0.7)
        if indicators.ma50 > 0:
            ax1.axhline(y=indicators.ma50, color=self.colors['ma'][1], 
                       linestyle='--', label='MA50', alpha=0.7)
        ax1.set_title(f'{symbol} - Analyse technique complète', 
                     fontsize=14, fontweight='bold', color='white')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. RSI
        self._plot_rsi(ax2, indicators.rsi)
        
        # 3. MACD
        self._plot_macd(ax3, indicators)
        
        # 4. Stochastique
        self._plot_stochastic(ax4, indicators)
        
        plt.tight_layout()
        return fig
    
    def create_multi_timeframe_chart(self, prices_1h: List[CryptoPrice],
                                    prices_4h: List[CryptoPrice],
                                    prices_1d: List[CryptoPrice],
                                    symbol: str,
                                    figsize: Tuple[int, int] = (15, 10)) -> Figure:
        """
        Crée un graphique multi-timeframes
        
        Returns:
            Figure avec 3 timeframes (1h, 4h, 1d)
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=figsize,
                                           facecolor=self.colors['background'])
        
        # 1h
        df_1h = self._prices_to_dataframe(prices_1h)
        if not df_1h.empty:
            self._plot_candlesticks(ax1, df_1h)
            ax1.set_title(f'{symbol} - 1 Heure', fontsize=12, fontweight='bold', color='white')
            ax1.grid(True, alpha=0.3)
        
        # 4h
        df_4h = self._prices_to_dataframe(prices_4h)
        if not df_4h.empty:
            self._plot_candlesticks(ax2, df_4h)
            ax2.set_title(f'{symbol} - 4 Heures', fontsize=12, fontweight='bold', color='white')
            ax2.grid(True, alpha=0.3)
        
        # 1d
        df_1d = self._prices_to_dataframe(prices_1d)
        if not df_1d.empty:
            self._plot_candlesticks(ax3, df_1d)
            ax3.set_title(f'{symbol} - 1 Jour', fontsize=12, fontweight='bold', color='white')
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _prices_to_dataframe(self, prices: List[CryptoPrice]) -> pd.DataFrame:
        """Convertit une liste de prix en DataFrame pandas"""
        if not prices:
            return pd.DataFrame()
        
        data = {
            'timestamp': [p.timestamp for p in prices],
            'open': [p.price_eur for p in prices],  # Simplifié
            'high': [p.high_24h if p.high_24h > 0 else p.price_eur for p in prices],
            'low': [p.low_24h if p.low_24h > 0 else p.price_eur for p in prices],
            'close': [p.price_eur for p in prices],
            'volume': [p.volume_24h for p in prices]
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Dessine les chandeliers"""
        for i in range(len(df)):
            row = df.iloc[i]
            timestamp = df.index[i]
            
            # Couleur selon hausse/baisse
            color = self.colors['up'] if row['close'] >= row['open'] else self.colors['down']
            
            # Mèche (high-low)
            ax.plot([timestamp, timestamp], [row['low'], row['high']], 
                   color=color, linewidth=1)
            
            # Corps du chandelier
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            
            ax.bar(timestamp, height, bottom=bottom, width=0.8, 
                  color=color, alpha=0.8, edgecolor=color)
        
        ax.set_ylabel('Prix (€)', color='white')
    
    def _plot_moving_averages(self, ax, df: pd.DataFrame, indicators: TechnicalIndicators):
        """Dessine les moyennes mobiles"""
        if indicators.ma20 > 0:
            ax.axhline(y=indicators.ma20, color=self.colors['ma'][0], 
                      linestyle='--', label='MA20', linewidth=2, alpha=0.7)
        
        if indicators.ma50 > 0:
            ax.axhline(y=indicators.ma50, color=self.colors['ma'][1], 
                      linestyle='--', label='MA50', linewidth=2, alpha=0.7)
        
        if indicators.ma200 > 0:
            ax.axhline(y=indicators.ma200, color=self.colors['ma'][2], 
                      linestyle='--', label='MA200', linewidth=2, alpha=0.7)
    
    def _plot_bollinger_bands(self, ax, df: pd.DataFrame, indicators: TechnicalIndicators):
        """Dessine les bandes de Bollinger"""
        if indicators.bollinger_upper > 0 and indicators.bollinger_lower > 0:
            ax.axhline(y=indicators.bollinger_upper, color='gray', 
                      linestyle=':', label='BB Upper', alpha=0.5)
            ax.axhline(y=indicators.bollinger_lower, color='gray', 
                      linestyle=':', label='BB Lower', alpha=0.5)
            
            # Zone entre les bandes
            ax.fill_between(df.index, indicators.bollinger_lower, 
                           indicators.bollinger_upper, alpha=0.1, color='gray')
    
    def _plot_support_resistance(self, ax, indicators: TechnicalIndicators):
        """Dessine support et résistance"""
        if indicators.support > 0:
            ax.axhline(y=indicators.support, color='green', 
                      linestyle='-.', label='Support', linewidth=2, alpha=0.7)
        
        if indicators.resistance > 0:
            ax.axhline(y=indicators.resistance, color='red', 
                      linestyle='-.', label='Résistance', linewidth=2, alpha=0.7)
    
    def _plot_volume(self, ax, df: pd.DataFrame):
        """Dessine les volumes"""
        colors = [self.colors['up'] if df.iloc[i]['close'] >= df.iloc[i]['open'] 
                 else self.colors['down'] for i in range(len(df))]
        
        ax.bar(df.index, df['volume'], color=colors, alpha=0.5)
        ax.set_ylabel('Volume', color='white')
        ax.set_xlabel('Temps', color='white')
    
    def _plot_rsi(self, ax, rsi: float):
        """Dessine le RSI"""
        ax.axhline(y=rsi, color=self.colors['volume'], linewidth=2)
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.5)
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.5)
        ax.fill_between([0, 1], 70, 100, alpha=0.1, color='red')
        ax.fill_between([0, 1], 0, 30, alpha=0.1, color='green')
        ax.set_ylabel('RSI', color='white')
        ax.set_ylim([0, 100])
        ax.grid(True, alpha=0.3)
        ax.text(0.5, rsi, f'RSI: {rsi:.1f}', color='white', fontweight='bold')
    
    def _plot_macd(self, ax, indicators: TechnicalIndicators):
        """Dessine le MACD"""
        # Simplifié - dans la vraie implémentation, il faudrait l'historique
        macd_color = 'green' if indicators.macd > indicators.macd_signal else 'red'
        
        ax.axhline(y=0, color='white', linestyle='-', alpha=0.3)
        ax.bar([0], [indicators.macd_histogram], color=macd_color, alpha=0.5, width=0.8)
        ax.plot([0], [indicators.macd], 'o', color='blue', label='MACD', markersize=10)
        ax.plot([0], [indicators.macd_signal], 'o', color='orange', label='Signal', markersize=10)
        
        ax.set_ylabel('MACD', color='white')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
    
    def _plot_stochastic(self, ax, indicators: TechnicalIndicators):
        """Dessine le Stochastique"""
        ax.axhline(y=indicators.stochastic_k, color='blue', linewidth=2, label='%K')
        ax.axhline(y=indicators.stochastic_d, color='orange', linewidth=2, label='%D')
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.5)
        ax.axhline(y=20, color='green', linestyle='--', alpha=0.5)
        ax.fill_between([0, 1], 80, 100, alpha=0.1, color='red')
        ax.fill_between([0, 1], 0, 20, alpha=0.1, color='green')
        ax.set_ylabel('Stochastique', color='white')
        ax.set_ylim([0, 100])
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
    
    def _create_empty_figure(self, figsize: Tuple[int, int]) -> Figure:
        """Crée une figure vide pour gérer les cas sans données"""
        fig, ax = plt.subplots(figsize=figsize, facecolor=self.colors['background'])
        ax.text(0.5, 0.5, 'Aucune donnée disponible', 
               ha='center', va='center', fontsize=16, color='gray')
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.axis('off')
        return fig
    
    def save_chart_to_bytes(self, fig: Figure) -> bytes:
        """Sauvegarde un graphique en bytes (pour Telegram)"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                   facecolor=self.colors['background'])
        buf.seek(0)
        return buf.getvalue()
    
    def save_chart_to_file(self, fig: Figure, filepath: str):
        """Sauvegarde un graphique dans un fichier"""
        fig.savefig(filepath, dpi=150, bbox_inches='tight', 
                   facecolor=self.colors['background'])
