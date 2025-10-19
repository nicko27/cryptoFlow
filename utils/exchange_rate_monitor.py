"""
Module de comparaison des taux de change
Compare Revolut vs taux publics vs Binance
"""

from typing import Dict, Optional
from datetime import datetime, timezone, timezone
from api.revolut_api import RevolutAPI
import requests


class ExchangeRateMonitor:
    """Moniteur des taux de change USD/EUR"""
    
    def __init__(self):
        self.revolut_api = RevolutAPI()
        self.session = requests.Session()
    
    def get_all_rates(self) -> Dict[str, Optional[float]]:
        """
        Récupère les taux de toutes les sources
        
        Returns:
            Dict avec clés: revolut, ecb, exchangerate_api, binance_implied
        """
        rates = {}
        
        # Revolut
        try:
            rates['revolut'] = self.revolut_api.get_exchange_rate("USD", "EUR")
        except:
            rates['revolut'] = None
        
        # ECB (Banque Centrale Européenne)
        try:
            rates['ecb'] = self._get_ecb_rate()
        except:
            rates['ecb'] = None
        
        # ExchangeRate API
        try:
            rates['exchangerate_api'] = self._get_exchangerate_api()
        except:
            rates['exchangerate_api'] = None
        
        # Taux implicite via Binance (BTC/USD vs BTC/EUR)
        try:
            rates['binance_implied'] = self._get_binance_implied_rate()
        except:
            rates['binance_implied'] = None
        
        rates['timestamp'] = datetime.now(timezone.utc)
        
        return rates
    
    def _get_ecb_rate(self) -> Optional[float]:
        """Taux BCE officiel"""
        url = "https://api.frankfurter.app/latest?from=USD&to=EUR"
        response = self.session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data['rates']['EUR'])
    
    def _get_exchangerate_api(self) -> Optional[float]:
        """Taux ExchangeRate-API"""
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = self.session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data['rates']['EUR'])
    
    def _get_binance_implied_rate(self) -> Optional[float]:
        """Calcule le taux implicite via BTC"""
        # BTC/USDT
        url_usd = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        resp_usd = self.session.get(url_usd, timeout=5)
        resp_usd.raise_for_status()
        btc_usd = float(resp_usd.json()['price'])
        
        # BTC/EUR
        url_eur = "https://api.binance.com/api/v3/ticker/price?symbol=BTCEUR"
        resp_eur = self.session.get(url_eur, timeout=5)
        resp_eur.raise_for_status()
        btc_eur = float(resp_eur.json()['price'])
        
        # Taux implicite
        return btc_eur / btc_usd
    
    def compare_rates(self) -> Dict:
        """
        Compare tous les taux et retourne statistiques
        
        Returns:
            Dict avec: rates, moyenne, écart-type, min, max, spread
        """
        all_rates = self.get_all_rates()
        
        # Extraire valeurs valides
        valid_rates = [v for k, v in all_rates.items() 
                      if k != 'timestamp' and v is not None]
        
        if not valid_rates:
            return {
                'error': 'Aucun taux disponible',
                'rates': all_rates
            }
        
        avg = sum(valid_rates) / len(valid_rates)
        min_rate = min(valid_rates)
        max_rate = max(valid_rates)
        spread_pct = ((max_rate - min_rate) / avg) * 100
        
        # Écart-type
        variance = sum((r - avg) ** 2 for r in valid_rates) / len(valid_rates)
        std_dev = variance ** 0.5
        
        return {
            'rates': all_rates,
            'stats': {
                'count': len(valid_rates),
                'average': avg,
                'std_dev': std_dev,
                'min': min_rate,
                'max': max_rate,
                'spread_pct': spread_pct
            },
            'best_source': min(all_rates.items(), 
                             key=lambda x: abs(x[1] - avg) if x[1] else 999)[0]
        }
    
    def generate_report(self) -> str:
        """Génère un rapport textuel"""
        comparison = self.compare_rates()
        
        if 'error' in comparison:
            return f"❌ {comparison['error']}"
        
        rates = comparison['rates']
        stats = comparison['stats']
        
        report = "💱 COMPARAISON TAUX DE CHANGE USD → EUR\n"
        report += "=" * 50 + "\n\n"
        
        report += "📊 Taux par source:\n"
        for source, rate in rates.items():
            if source == 'timestamp':
                continue
            if rate:
                diff_from_avg = ((rate - stats['average']) / stats['average']) * 100
                indicator = "✓" if abs(diff_from_avg) < 0.1 else "⚠"
                report += f"  {indicator} {source:20s}: {rate:.6f} ({diff_from_avg:+.2f}%)\n"
            else:
                report += f"  ✗ {source:20s}: INDISPONIBLE\n"
        
        report += f"\n📈 Statistiques:\n"
        report += f"  • Moyenne      : {stats['average']:.6f}\n"
        report += f"  • Écart-type   : {stats['std_dev']:.6f}\n"
        report += f"  • Min          : {stats['min']:.6f}\n"
        report += f"  • Max          : {stats['max']:.6f}\n"
        report += f"  • Spread       : {stats['spread_pct']:.3f}%\n"
        
        report += f"\n✅ Meilleure source: {comparison['best_source']}\n"
        
        if stats['spread_pct'] > 1:
            report += "\n⚠️  Spread élevé - Vérifier les sources\n"
        
        return report


def test_rates():
    """Test du module"""
    monitor = ExchangeRateMonitor()
    
    print("\n🔍 Test des taux de change...\n")
    print(monitor.generate_report())
    
    print("\n" + "="*50)
    print("💰 Exemple conversion:")
    print("  100 USD =", f"{100 * monitor.compare_rates()['stats']['average']:.2f}", "EUR")


if __name__ == "__main__":
    test_rates()
