"""
Report Service - Génération de rapports complets
"""

from typing import Dict, List
from datetime import datetime, timedelta
from core.models import MarketData, Prediction, OpportunityScore
from io import StringIO


class ReportService:
    """Service de génération de rapports"""
    
    def generate_complete_report(self,
                                 markets_data: Dict[str, MarketData],
                                 predictions: Dict[str, Prediction],
                                 opportunities: Dict[str, OpportunityScore],
                                 stats: Dict = None) -> str:
        """Génère un rapport complet"""
        
        report = StringIO()
        
        # En-tête
        report.write("=" * 70 + "\n")
        report.write("RAPPORT COMPLET - CRYPTO BOT v3.0\n")
        report.write(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        report.write("=" * 70 + "\n\n")
        
        # Résumé exécutif
        report.write(self._generate_executive_summary(markets_data, opportunities))
        report.write("\n")
        
        # Analyse par crypto
        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            prediction = predictions.get(symbol)
            opportunity = opportunities.get(symbol)
            
            report.write(self._generate_crypto_section(symbol, market, prediction, opportunity))
            report.write("\n")
        
        # Comparaison
        report.write(self._generate_comparison_section(markets_data, opportunities))
        report.write("\n")
        
        # Recommandations
        report.write(self._generate_recommendations(markets_data, opportunities))
        report.write("\n")
        
        # Statistiques
        if stats:
            report.write(self._generate_stats_section(stats))
            report.write("\n")
        
        # Pied de page
        report.write("=" * 70 + "\n")
        report.write("Fin du rapport\n")
        report.write("=" * 70 + "\n")
        
        return report.getvalue()
    
    def _generate_executive_summary(self, markets_data: Dict[str, MarketData],
                                   opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé exécutif"""
        
        summary = "📊 RÉSUMÉ EXÉCUTIF\n"
        summary += "-" * 70 + "\n\n"
        
        # Meilleure opportunité
        best_opp = max(opportunities.items(), key=lambda x: x[1].score)
        summary += f"🎯 Meilleure opportunité : {best_opp[0]} (Score: {best_opp[1].score}/10)\n"
        
        # Pire opportunité
        worst_opp = min(opportunities.items(), key=lambda x: x[1].score)
        summary += f"⚠️ À éviter : {worst_opp[0]} (Score: {worst_opp[1].score}/10)\n\n"
        
        # Tendance générale
        avg_change = sum(m.current_price.change_24h for m in markets_data.values()) / len(markets_data)
        trend = "📈 Haussière" if avg_change > 0 else "📉 Baissière"
        summary += f"Tendance générale 24h : {trend} ({avg_change:+.2f}%)\n\n"
        
        return summary
    
    def _generate_crypto_section(self, symbol: str, market: MarketData,
                                prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Section pour une crypto"""
        
        section = f"{'━' * 70}\n"
        section += f"💎 {symbol}\n"
        section += f"{'━' * 70}\n\n"
        
        # Prix et changement
        price = market.current_price
        section += f"Prix actuel : {price.price_eur:.2f}€\n"
        section += f"Changement 24h : {price.change_24h:+.2f}%\n"
        section += f"Volume 24h : {price.volume_24h:,.0f}\n\n"
        
        # Indicateurs techniques
        ti = market.technical_indicators
        section += "Indicateurs techniques :\n"
        section += f"  • RSI : {ti.rsi:.0f}"
        if ti.rsi < 30:
            section += " (survendu 🟢)\n"
        elif ti.rsi > 70:
            section += " (suracheté 🔴)\n"
        else:
            section += "\n"
        
        section += f"  • MA20 : {ti.ma20:.2f}€\n"
        section += f"  • Support : {ti.support:.2f}€\n"
        section += f"  • Résistance : {ti.resistance:.2f}€\n\n"
        
        # Prédiction
        if prediction:
            section += f"🔮 Prédiction : {prediction.direction} {prediction.prediction_type.value}\n"
            section += f"   Confiance : {prediction.confidence}%\n"
            section += f"   Cible haute : {prediction.target_high:.2f}€\n"
            section += f"   Cible basse : {prediction.target_low:.2f}€\n\n"
        
        # Opportunité
        if opportunity:
            section += f"⭐ Score opportunité : {opportunity.score}/10\n"
            section += f"   {opportunity.recommendation}\n\n"
            
            if opportunity.reasons:
                section += "   Raisons :\n"
                for reason in opportunity.reasons:
                    section += f"   • {reason}\n"
                section += "\n"
        
        # Fear & Greed
        if market.fear_greed_index:
            section += f"😱 Fear & Greed Index : {market.fear_greed_index}/100\n\n"
        
        return section
    
    def _generate_comparison_section(self, markets_data: Dict[str, MarketData],
                                    opportunities: Dict[str, OpportunityScore]) -> str:
        """Section comparative"""
        
        section = "📊 COMPARAISON\n"
        section += "-" * 70 + "\n\n"
        
        # Tableau comparatif
        section += f"{'Symbole':<10} {'Prix':<12} {'24h':<10} {'RSI':<8} {'Score':<8}\n"
        section += "-" * 70 + "\n"
        
        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            opp = opportunities.get(symbol)
            
            price = market.current_price.price_eur
            change = market.current_price.change_24h
            rsi = market.technical_indicators.rsi
            score = opp.score if opp else 0
            
            section += f"{symbol:<10} {price:<12.2f} {change:>+6.2f}% {rsi:>6.0f} {score:>6}/10\n"
        
        section += "\n"
        return section
    
    def _generate_recommendations(self, markets_data: Dict[str, MarketData],
                                 opportunities: Dict[str, OpportunityScore]) -> str:
        """Recommandations"""
        
        section = "💡 RECOMMANDATIONS\n"
        section += "-" * 70 + "\n\n"
        
        # Trier par score d'opportunité
        sorted_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)
        
        # Achats recommandés
        section += "À acheter maintenant :\n"
        buy_recommendations = [item for item in sorted_opps if item[1].score >= 7]
        
        if buy_recommendations:
            for symbol, opp in buy_recommendations:
                market = markets_data[symbol]
                section += f"  ✅ {symbol} à {market.current_price.price_eur:.2f}€ "
                section += f"(Score: {opp.score}/10)\n"
        else:
            section += "  Aucune opportunité excellente actuellement\n"
        
        section += "\n"
        
        # À surveiller
        section += "À surveiller :\n"
        watch_recommendations = [item for item in sorted_opps if 5 <= item[1].score < 7]
        
        if watch_recommendations:
            for symbol, opp in watch_recommendations[:3]:
                market = markets_data[symbol]
                section += f"  👀 {symbol} à {market.current_price.price_eur:.2f}€ "
                section += f"(Score: {opp.score}/10)\n"
        else:
            section += "  Aucune crypto à surveiller particulièrement\n"
        
        section += "\n"
        
        # À éviter
        section += "À éviter pour le moment :\n"
        avoid_recommendations = [item for item in sorted_opps if item[1].score < 5]
        
        if avoid_recommendations:
            for symbol, opp in avoid_recommendations:
                section += f"  ❌ {symbol} (Score: {opp.score}/10)\n"
        else:
            section += "  Toutes les cryptos ont un score correct\n"
        
        section += "\n"
        
        return section
    
    def _generate_stats_section(self, stats: Dict) -> str:
        """Section statistiques"""
        
        section = "📈 STATISTIQUES\n"
        section += "-" * 70 + "\n\n"
        
        section += f"Vérifications totales : {stats.get('total_checks', 0)}\n"
        section += f"Alertes envoyées : {stats.get('total_alerts', 0)}\n"
        section += f"Erreurs : {stats.get('total_errors', 0)}\n"
        section += f"Moyenne vérifications/jour : {stats.get('avg_checks_per_day', 0):.1f}\n\n"
        
        return section
    
    def generate_html_report(self, text_report: str) -> str:
        """Convertit le rapport en HTML"""
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Crypto Bot Report</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .header {
            border-bottom: 2px solid #007acc;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Crypto Bot Report</h1>
    </div>
    <pre>{}</pre>
</body>
</html>
        """.format(text_report)
        
        return html
