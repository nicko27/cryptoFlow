"""
Multi-Crypto Analysis - Analyse comparative et corrélations entre cryptos
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from scipy.stats import pearsonr
from sklearn.decomposition import PCA

from core.models import CryptoPrice, MarketData


class MultiCryptoAnalyzer:
    """Analyseur multi-cryptos"""
    
    def __init__(self):
        self.price_data: Dict[str, List[CryptoPrice]] = {}
        self.market_data_cache: Dict[str, MarketData] = {}
    
    def add_price_data(self, symbol: str, prices: List[CryptoPrice]):
        """Ajoute des données de prix pour un symbole"""
        self.price_data[symbol] = prices
    
    def calculate_correlations(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Calcule la matrice de corrélation entre cryptos
        
        Returns:
            DataFrame avec matrice de corrélation
        """
        if symbols is None:
            symbols = list(self.price_data.keys())
        
        if len(symbols) < 2:
            return pd.DataFrame()
        
        # Créer DataFrame avec tous les prix
        price_dict = {}
        
        for symbol in symbols:
            if symbol in self.price_data and self.price_data[symbol]:
                prices = [p.price_eur for p in self.price_data[symbol]]
                price_dict[symbol] = prices
        
        if not price_dict:
            return pd.DataFrame()
        
        df = pd.DataFrame(price_dict)
        
        # Calculer la matrice de corrélation
        correlation_matrix = df.corr()
        
        return correlation_matrix
    
    def find_correlated_pairs(self, threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        Trouve les paires de cryptos fortement corrélées
        
        Args:
            threshold: Seuil de corrélation (0-1)
        
        Returns:
            Liste de tuples (symbol1, symbol2, correlation)
        """
        corr_matrix = self.calculate_correlations()
        
        if corr_matrix.empty:
            return []
        
        pairs = []
        symbols = list(corr_matrix.columns)
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols[i+1:], i+1):
                corr = corr_matrix.loc[sym1, sym2]
                
                if abs(corr) >= threshold:
                    pairs.append((sym1, sym2, corr))
        
        # Trier par corrélation décroissante
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        return pairs
    
    def calculate_beta(self, symbol: str, market_symbol: str = 'BTC') -> Optional[float]:
        """
        Calcule le beta d'une crypto par rapport au marché (BTC)
        
        Args:
            symbol: Symbole de la crypto
            market_symbol: Symbole du marché de référence
        
        Returns:
            Beta (volatilité relative au marché)
        """
        if symbol not in self.price_data or market_symbol not in self.price_data:
            return None
        
        # Calculer les rendements
        symbol_prices = [p.price_eur for p in self.price_data[symbol]]
        market_prices = [p.price_eur for p in self.price_data[market_symbol]]
        
        if len(symbol_prices) < 2 or len(market_prices) < 2:
            return None
        
        # Aligner les longueurs
        min_len = min(len(symbol_prices), len(market_prices))
        symbol_prices = symbol_prices[-min_len:]
        market_prices = market_prices[-min_len:]
        
        # Rendements
        symbol_returns = [(symbol_prices[i] - symbol_prices[i-1]) / symbol_prices[i-1] 
                         for i in range(1, len(symbol_prices))]
        market_returns = [(market_prices[i] - market_prices[i-1]) / market_prices[i-1]
                         for i in range(1, len(market_prices))]
        
        # Calcul du beta: Cov(symbol, market) / Var(market)
        covariance = np.cov(symbol_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        if market_variance == 0:
            return None
        
        beta = covariance / market_variance
        
        return beta
    
    def compare_performance(self, symbols: List[str], days: int = 30) -> pd.DataFrame:
        """
        Compare les performances de plusieurs cryptos
        
        Returns:
            DataFrame avec métriques de performance
        """
        results = []
        
        for symbol in symbols:
            if symbol not in self.price_data or not self.price_data[symbol]:
                continue
            
            prices = self.price_data[symbol]
            
            if len(prices) < 2:
                continue
            
            # Filtrer sur la période
            cutoff = datetime.now() - timedelta(days=days)
            recent_prices = [p for p in prices if p.timestamp >= cutoff]
            
            if len(recent_prices) < 2:
                continue
            
            first_price = recent_prices[0].price_eur
            last_price = recent_prices[-1].price_eur
            
            # Calculs
            price_change = last_price - first_price
            price_change_pct = (price_change / first_price) * 100
            
            price_values = [p.price_eur for p in recent_prices]
            volatility = np.std(price_values) / np.mean(price_values) * 100
            
            high = max(price_values)
            low = min(price_values)
            range_pct = ((high - low) / low) * 100
            
            # Calcul rendement annualisé
            days_elapsed = (recent_prices[-1].timestamp - recent_prices[0].timestamp).days
            if days_elapsed > 0:
                annualized_return = ((last_price / first_price) ** (365 / days_elapsed) - 1) * 100
            else:
                annualized_return = 0
            
            results.append({
                'Symbol': symbol,
                'Current_Price': last_price,
                'Change_%': price_change_pct,
                'Volatility_%': volatility,
                'High': high,
                'Low': low,
                'Range_%': range_pct,
                'Annualized_Return_%': annualized_return
            })
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df = df.sort_values('Change_%', ascending=False)
        
        return df
    
    def calculate_portfolio_diversification(self, positions: Dict[str, float]) -> Dict:
        """
        Analyse la diversification d'un portfolio
        
        Args:
            positions: Dict {symbol: weight_pct}
        
        Returns:
            Dict avec métriques de diversification
        """
        if not positions:
            return {'error': 'No positions'}
        
        symbols = list(positions.keys())
        
        # Calcul de l'indice de Herfindahl-Hirschman
        weights = list(positions.values())
        hhi = sum(w**2 for w in weights)
        
        # Nombre équivalent de positions
        n_effective = 10000 / hhi if hhi > 0 else 0
        
        # Corrélations moyennes
        corr_matrix = self.calculate_correlations(symbols)
        
        if not corr_matrix.empty:
            # Corrélation moyenne (hors diagonale)
            corr_values = []
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols[i+1:], i+1):
                    if sym1 in corr_matrix.columns and sym2 in corr_matrix.columns:
                        corr_values.append(corr_matrix.loc[sym1, sym2])
            
            avg_correlation = np.mean(corr_values) if corr_values else 0
        else:
            avg_correlation = 0
        
        # Évaluation
        if hhi > 2500:
            diversification_level = 'LOW'
            message = "⚠️ Portfolio peu diversifié"
        elif hhi > 1500:
            diversification_level = 'MEDIUM'
            message = "⚡ Diversification modérée"
        else:
            diversification_level = 'HIGH'
            message = "✅ Portfolio bien diversifié"
        
        return {
            'herfindahl_index': hhi,
            'effective_positions': n_effective,
            'avg_correlation': avg_correlation,
            'diversification_level': diversification_level,
            'num_positions': len(positions),
            'largest_position_pct': max(weights),
            'message': message
        }
    
    def identify_market_leaders(self) -> List[Dict]:
        """
        Identifie les leaders du marché
        
        Returns:
            Liste des cryptos avec les meilleures performances
        """
        df = self.compare_performance(list(self.price_data.keys()), days=7)
        
        if df.empty:
            return []
        
        # Trier par performance
        df_sorted = df.sort_values('Change_%', ascending=False)
        
        leaders = []
        for _, row in df_sorted.head(5).iterrows():
            leaders.append({
                'symbol': row['Symbol'],
                'change_pct': row['Change_%'],
                'volatility': row['Volatility_%'],
                'status': '📈 Leader' if row['Change_%'] > 0 else '📉 Perdant'
            })
        
        return leaders
    
    def detect_sector_rotation(self, categories: Dict[str, List[str]]) -> Dict:
        """
        Détecte les rotations sectorielles
        
        Args:
            categories: Dict {category_name: [symbols]}
            Exemple: {'Layer1': ['BTC', 'ETH', 'SOL'], 'DeFi': ['UNI', 'AAVE']}
        
        Returns:
            Dict avec performance par secteur
        """
        sector_performance = {}
        
        for sector, symbols in categories.items():
            # Calculer la performance moyenne du secteur
            sector_symbols = [s for s in symbols if s in self.price_data]
            
            if not sector_symbols:
                continue
            
            df = self.compare_performance(sector_symbols, days=7)
            
            if not df.empty:
                avg_change = df['Change_%'].mean()
                avg_vol = df['Volatility_%'].mean()
                
                sector_performance[sector] = {
                    'avg_change_pct': avg_change,
                    'avg_volatility': avg_vol,
                    'num_cryptos': len(sector_symbols),
                    'trend': '📈 Haussier' if avg_change > 2 else '📉 Baissier' if avg_change < -2 else '➡️ Neutre'
                }
        
        return sector_performance
    
    def calculate_market_dominance(self, symbols: List[str]) -> Dict[str, float]:
        """
        Calcule la dominance de marché de chaque crypto
        
        Returns:
            Dict {symbol: dominance_%}
        """
        # Récupérer les market caps (approximés via volumes)
        market_caps = {}
        
        for symbol in symbols:
            if symbol in self.price_data and self.price_data[symbol]:
                latest = self.price_data[symbol][-1]
                # Market cap approximé = prix * volume 24h
                market_cap = latest.price_eur * latest.volume_24h
                market_caps[symbol] = market_cap
        
        if not market_caps:
            return {}
        
        total_market_cap = sum(market_caps.values())
        
        dominance = {
            symbol: (cap / total_market_cap * 100)
            for symbol, cap in market_caps.items()
        }
        
        return dict(sorted(dominance.items(), key=lambda x: x[1], reverse=True))
    
    def pca_analysis(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Analyse en Composantes Principales (PCA)
        
        Returns:
            Dict avec résultats PCA
        """
        if symbols is None:
            symbols = list(self.price_data.keys())
        
        if len(symbols) < 2:
            return {'error': 'Not enough data'}
        
        # Préparer les données
        price_dict = {}
        
        for symbol in symbols:
            if symbol in self.price_data and self.price_data[symbol]:
                prices = [p.price_eur for p in self.price_data[symbol]]
                price_dict[symbol] = prices
        
        if len(price_dict) < 2:
            return {'error': 'Not enough valid symbols'}
        
        df = pd.DataFrame(price_dict)
        
        # Normaliser
        df_normalized = (df - df.mean()) / df.std()
        
        # PCA
        pca = PCA(n_components=min(2, len(symbols)))
        pca.fit(df_normalized.T)
        
        return {
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'components': pca.components_.tolist(),
            'n_components': pca.n_components_,
            'cumulative_variance': np.cumsum(pca.explained_variance_ratio_).tolist()
        }
