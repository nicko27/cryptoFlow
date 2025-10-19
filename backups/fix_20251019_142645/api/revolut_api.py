"""
API Client pour Revolut - Taux de change
"""

import requests
from typing import Optional
from datetime import datetime, timezone, timezone


class RevolutAPI:
    """Client API Revolut pour taux de change"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self._rate_cache = {}
        self._cache_time = None
    
    def get_exchange_rate(self, from_currency: str = "USD", to_currency: str = "EUR") -> Optional[float]:
        """
        Récupère le taux de change entre deux devises
        
        Args:
            from_currency: Devise source (défaut: USD)
            to_currency: Devise cible (défaut: EUR)
        
        Returns:
            Taux de change ou None si erreur
        """
        # Vérifier cache (valide 1h)
        cache_key = f"{from_currency}_{to_currency}"
        if self._is_cache_valid() and cache_key in self._rate_cache:
            return self._rate_cache[cache_key]
        
        try:
            # Utiliser l'API publique de taux de change
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if "rates" in data and to_currency in data["rates"]:
                rate = float(data["rates"][to_currency])
                
                # Mettre en cache
                self._rate_cache[cache_key] = rate
                self._cache_time = datetime.now(timezone.utc)
                
                return rate
            
            return None
        
        except Exception as e:
            print(f"Erreur récupération taux Revolut: {e}")
            
            # Fallback sur cache même expiré
            if cache_key in self._rate_cache:
                return self._rate_cache[cache_key]
            
            # Valeur par défaut si échec total
            if from_currency == "USD" and to_currency == "EUR":
                return 0.92
            
            return None
    
    def _is_cache_valid(self) -> bool:
        """Vérifie si le cache est valide (< 1h)"""
        if not self._cache_time:
            return False
        
        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < 3600  # 1 heure
    
    def get_multiple_rates(self, from_currency: str, to_currencies: list) -> dict:
        """
        Récupère plusieurs taux de change
        
        Args:
            from_currency: Devise source
            to_currencies: Liste des devises cibles
        
        Returns:
            Dict {devise: taux}
        """
        rates = {}
        
        for to_currency in to_currencies:
            rate = self.get_exchange_rate(from_currency, to_currency)
            if rate:
                rates[to_currency] = rate
        
        return rates
    
    def convert(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Convertit un montant d'une devise à une autre
        
        Args:
            amount: Montant à convertir
            from_currency: Devise source
            to_currency: Devise cible
        
        Returns:
            Montant converti ou None
        """
        rate = self.get_exchange_rate(from_currency, to_currency)
        if rate:
            return amount * rate
        return None
