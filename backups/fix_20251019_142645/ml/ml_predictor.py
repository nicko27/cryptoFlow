"""
Machine Learning Module - Prédictions avancées avec LSTM, Random Forest, etc.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path

from core.models import CryptoPrice, MarketData, TechnicalIndicators, Prediction, PredictionType


class MLPredictor:
    """Prédicteur ML pour crypto"""
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        Args:
            model_type: 'random_forest', 'gradient_boosting', ou 'lstm'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = MinMaxScaler()
        self.feature_columns = []
        self.is_trained = False
        
        self.models_dir = Path("ml/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_features(self, market_data: MarketData, 
                        price_history: List[CryptoPrice]) -> np.ndarray:
        """
        Prépare les features pour le ML
        
        Returns:
            Array numpy avec les features
        """
        features = {}
        
        # Features de prix
        if price_history and len(price_history) >= 20:
            prices = [p.price_eur for p in price_history[-20:]]
            
            features['price_mean'] = np.mean(prices)
            features['price_std'] = np.std(prices)
            features['price_min'] = np.min(prices)
            features['price_max'] = np.max(prices)
            
            # Momentum
            features['momentum_5'] = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
            features['momentum_10'] = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
            features['momentum_20'] = (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0
            
            # Volatilité
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            features['volatility'] = np.std(returns) if returns else 0
        else:
            # Valeurs par défaut si pas assez d'historique
            features.update({
                'price_mean': market_data.current_price.price_eur,
                'price_std': 0,
                'price_min': market_data.current_price.price_eur,
                'price_max': market_data.current_price.price_eur,
                'momentum_5': 0,
                'momentum_10': 0,
                'momentum_20': 0,
                'volatility': 0
            })
        
        # Indicateurs techniques
        ti = market_data.technical_indicators
        features['rsi'] = ti.rsi
        features['macd'] = ti.macd
        features['macd_signal'] = ti.macd_signal
        features['macd_histogram'] = ti.macd_histogram
        
        # Normalisation des MA
        current_price = market_data.current_price.price_eur
        features['ma20_ratio'] = (current_price - ti.ma20) / current_price if ti.ma20 > 0 else 0
        features['ma50_ratio'] = (current_price - ti.ma50) / current_price if ti.ma50 > 0 else 0
        features['ma200_ratio'] = (current_price - ti.ma200) / current_price if ti.ma200 > 0 else 0
        
        # Support/Résistance
        features['distance_support'] = (current_price - ti.support) / current_price if ti.support > 0 else 0
        features['distance_resistance'] = (ti.resistance - current_price) / current_price if ti.resistance > 0 else 0
        
        # Volume
        features['volume_24h'] = market_data.current_price.volume_24h
        features['change_24h'] = market_data.current_price.change_24h
        
        # Fear & Greed
        features['fear_greed'] = market_data.fear_greed_index if market_data.fear_greed_index else 50
        
        # Funding rate
        features['funding_rate'] = market_data.funding_rate if market_data.funding_rate else 0
        
        # Stocker les noms de colonnes lors de la première utilisation
        if not self.feature_columns:
            self.feature_columns = list(features.keys())
        
        # Convertir en array numpy
        return np.array([features[col] for col in self.feature_columns]).reshape(1, -1)
    
    def train(self, training_data: List[Dict], target_hours: int = 6):
        """
        Entraîne le modèle
        
        Args:
            training_data: Liste de dicts avec features et target_price
            target_hours: Nombre d'heures pour la prédiction
        """
        if len(training_data) < 100:
            print(f"⚠️ Pas assez de données pour l'entraînement ({len(training_data)} < 100)")
            return False
        
        # Préparer les données
        X = np.array([d['features'] for d in training_data])
        y = np.array([d['target_price'] for d in training_data])
        
        # Normaliser
        X_scaled = self.scaler.fit_transform(X)
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Créer et entraîner le modèle
        if self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        else:
            print(f"❌ Type de modèle non supporté: {self.model_type}")
            return False
        
        print(f"🤖 Entraînement du modèle {self.model_type}...")
        self.model.fit(X_train, y_train)
        
        # Évaluation
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"✅ Entraînement terminé!")
        print(f"   Score train: {train_score:.4f}")
        print(f"   Score test: {test_score:.4f}")
        
        self.is_trained = True
        
        # Sauvegarder le modèle
        self.save_model()
        
        return True
    
    def predict_price(self, market_data: MarketData, 
                     price_history: List[CryptoPrice],
                     hours_ahead: int = 6) -> Tuple[float, float]:
        """
        Prédit le prix futur
        
        Returns:
            (predicted_price, confidence)
        """
        if not self.is_trained or self.model is None:
            # Essayer de charger un modèle sauvegardé
            if not self.load_model():
                # Retour sur règle simple si pas de modèle
                return self._simple_prediction(market_data)
        
        # Préparer les features
        features = self.prepare_features(market_data, price_history)
        
        # Normaliser
        features_scaled = self.scaler.transform(features)
        
        # Prédire
        predicted_price = self.model.predict(features_scaled)[0]
        
        # Calculer confiance (simplifié)
        current_price = market_data.current_price.price_eur
        price_change_pct = abs((predicted_price - current_price) / current_price) * 100
        
        # Confiance inversement proportionnelle au changement
        confidence = max(50, 100 - price_change_pct * 5)
        
        return predicted_price, min(95, confidence)
    
    def _simple_prediction(self, market_data: MarketData) -> Tuple[float, float]:
        """Prédiction simple basée sur règles si pas de ML"""
        current_price = market_data.current_price.price_eur
        ti = market_data.technical_indicators
        
        # Facteur de tendance basé sur RSI et MACD
        trend_factor = 0
        
        if ti.rsi < 30:
            trend_factor += 0.02
        elif ti.rsi > 70:
            trend_factor -= 0.02
        
        if ti.macd_histogram > 0:
            trend_factor += 0.01
        else:
            trend_factor -= 0.01
        
        predicted_price = current_price * (1 + trend_factor)
        confidence = 55
        
        return predicted_price, confidence
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Retourne l'importance des features"""
        if not self.is_trained or self.model is None:
            return None
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return {
                col: float(imp) 
                for col, imp in zip(self.feature_columns, importances)
            }
        
        return None
    
    def save_model(self, filename: Optional[str] = None):
        """Sauvegarde le modèle"""
        if not self.is_trained or self.model is None:
            return
        
        if filename is None:
            filename = f"{self.model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pkl"
        
        filepath = self.models_dir / filename
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type
        }, filepath)
        
        print(f"💾 Modèle sauvegardé: {filepath}")
    
    def load_model(self, filename: Optional[str] = None) -> bool:
        """Charge un modèle sauvegardé"""
        if filename is None:
            # Chercher le modèle le plus récent
            models = list(self.models_dir.glob(f"{self.model_type}_*.pkl"))
            if not models:
                return False
            filepath = max(models, key=lambda p: p.stat().st_mtime)
        else:
            filepath = self.models_dir / filename
        
        if not filepath.exists():
            return False
        
        try:
            data = joblib.load(filepath)
            self.model = data['model']
            self.scaler = data['scaler']
            self.feature_columns = data['feature_columns']
            self.model_type = data['model_type']
            self.is_trained = True
            
            print(f"📂 Modèle chargé: {filepath}")
            return True
        
        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            return False


class EnsemblePredictor:
    """Ensemble de plusieurs modèles pour prédictions robustes"""
    
    def __init__(self):
        self.predictors = {
            'rf': MLPredictor('random_forest'),
            'gb': MLPredictor('gradient_boosting')
        }
        self.weights = {'rf': 0.5, 'gb': 0.5}
    
    def predict(self, market_data: MarketData, 
               price_history: List[CryptoPrice],
               hours_ahead: int = 6) -> Tuple[float, float]:
        """
        Prédiction par ensemble de modèles
        
        Returns:
            (predicted_price, confidence)
        """
        predictions = []
        confidences = []
        
        for name, predictor in self.predictors.items():
            try:
                pred, conf = predictor.predict_price(market_data, price_history, hours_ahead)
                predictions.append(pred * self.weights[name])
                confidences.append(conf * self.weights[name])
            except Exception as e:
                print(f"⚠️ Erreur prédiction {name}: {e}")
        
        if not predictions:
            # Fallback
            return market_data.current_price.price_eur, 50.0
        
        final_prediction = sum(predictions)
        final_confidence = sum(confidences)
        
        return final_prediction, min(95, final_confidence)
    
    def train_all(self, training_data: List[Dict]):
        """Entraîne tous les modèles"""
        for name, predictor in self.predictors.items():
            print(f"\n🤖 Entraînement modèle: {name}")
            predictor.train(training_data)


class PatternRecognition:
    """Reconnaissance de patterns chartistes"""
    
    @staticmethod
    def detect_head_and_shoulders(prices: List[float]) -> bool:
        """Détecte un pattern tête-épaules"""
        if len(prices) < 50:
            return False
        
        # Simplifié - chercher 3 pics
        prices_array = np.array(prices[-50:])
        
        # Trouver les pics locaux
        peaks = []
        for i in range(2, len(prices_array) - 2):
            if prices_array[i] > prices_array[i-1] and prices_array[i] > prices_array[i+1]:
                if prices_array[i] > prices_array[i-2] and prices_array[i] > prices_array[i+2]:
                    peaks.append((i, prices_array[i]))
        
        if len(peaks) < 3:
            return False
        
        # Vérifier pattern: épaule - tête - épaule
        # (pic central plus haut que les 2 autres)
        for i in range(1, len(peaks) - 1):
            left_shoulder = peaks[i-1][1]
            head = peaks[i][1]
            right_shoulder = peaks[i+1][1]
            
            if head > left_shoulder and head > right_shoulder:
                if abs(left_shoulder - right_shoulder) / left_shoulder < 0.05:  # 5% tolérance
                    return True
        
        return False
    
    @staticmethod
    def detect_double_bottom(prices: List[float]) -> bool:
        """Détecte un double bottom (bullish)"""
        if len(prices) < 30:
            return False
        
        prices_array = np.array(prices[-30:])
        
        # Trouver les creux
        troughs = []
        for i in range(2, len(prices_array) - 2):
            if prices_array[i] < prices_array[i-1] and prices_array[i] < prices_array[i+1]:
                if prices_array[i] < prices_array[i-2] and prices_array[i] < prices_array[i+2]:
                    troughs.append((i, prices_array[i]))
        
        if len(troughs) < 2:
            return False
        
        # Vérifier si 2 creux similaires
        for i in range(len(troughs) - 1):
            trough1 = troughs[i][1]
            trough2 = troughs[i+1][1]
            
            if abs(trough1 - trough2) / trough1 < 0.03:  # 3% tolérance
                return True
        
        return False
    
    @staticmethod
    def detect_golden_cross(ma50: float, ma200: float, 
                           ma50_prev: float, ma200_prev: float) -> bool:
        """Détecte une golden cross (MA50 croise MA200 à la hausse)"""
        if ma50 <= 0 or ma200 <= 0 or ma50_prev <= 0 or ma200_prev <= 0:
            return False
        
        # Avant: MA50 < MA200, Maintenant: MA50 > MA200
        return ma50_prev < ma200_prev and ma50 > ma200
    
    @staticmethod
    def detect_death_cross(ma50: float, ma200: float,
                          ma50_prev: float, ma200_prev: float) -> bool:
        """Détecte une death cross (MA50 croise MA200 à la baisse)"""
        if ma50 <= 0 or ma200 <= 0 or ma50_prev <= 0 or ma200_prev <= 0:
            return False
        
        # Avant: MA50 > MA200, Maintenant: MA50 < MA200
        return ma50_prev > ma200_prev and ma50 < ma200
