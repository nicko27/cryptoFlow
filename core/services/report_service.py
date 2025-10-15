"""
Report Service - Génération de rapports complets
"""

from typing import Dict, List, Optional
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

        has_market_data = bool(markets_data)
        has_opportunities = bool(opportunities)

        if not has_market_data and not has_opportunities:
            summary += "Données insuffisantes pour générer un résumé exécutif.\n\n"
            return summary

        if has_opportunities:
            # Meilleure opportunité
            best_opp = max(opportunities.items(), key=lambda x: x[1].score)
            summary += (
                f"🎯 Meilleure opportunité : {best_opp[0]} "
                f"(Score: {best_opp[1].score}/10)\n"
            )

            # Pire opportunité
            worst_opp = min(opportunities.items(), key=lambda x: x[1].score)
            summary += (
                f"⚠️ À éviter : {worst_opp[0]} "
                f"(Score: {worst_opp[1].score}/10)\n\n"
            )
        else:
            summary += "Aucune opportunité analysée pour le moment.\n\n"

        if has_market_data:
            changes = self._collect_valid_changes(markets_data)
            if changes:
                avg_change = sum(changes) / len(changes)
                trend = "📈 Haussière" if avg_change > 0 else "📉 Baissière"
                summary += (
                    f"Tendance générale 24h : {trend} "
                    f"({avg_change:+.2f}%)\n\n"
                )
            else:
                summary += "Tendance générale 24h : données indisponibles\n\n"
        else:
            summary += "Données de marché indisponibles pour le moment.\n\n"

        return summary
    
    def _generate_crypto_section(self, symbol: str, market: MarketData,
                                prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Section pour une crypto"""
        
        section = f"{'━' * 70}\n"
        section += f"💎 {symbol}\n"
        section += f"{'━' * 70}\n\n"
        
        # Prix et changement
        price_value = self._format_price(market)
        section += f"Prix actuel : {price_value}\n"

        change_value = self._format_change(market)
        section += f"Changement 24h : {change_value}\n"

        volume_value = self._format_volume(market)
        section += f"Volume 24h : {volume_value}\n\n"

        # Indicateurs techniques
        ti = market.technical_indicators
        if ti:
            section += "Indicateurs techniques :\n"
            rsi_display = "indisponible" if ti.rsi is None else f"{ti.rsi:.0f}"
            section += f"  • RSI : {rsi_display}"
            if ti.rsi is not None:
                if ti.rsi < 30:
                    section += " (survendu 🟢)\n"
                elif ti.rsi > 70:
                    section += " (suracheté 🔴)\n"
                else:
                    section += "\n"
            else:
                section += "\n"

            ma20_display = "indisponible" if ti.ma20 is None else f"{ti.ma20:.2f}€"
            support_display = "indisponible" if ti.support is None else f"{ti.support:.2f}€"
            resistance_display = "indisponible" if ti.resistance is None else f"{ti.resistance:.2f}€"

            section += f"  • MA20 : {ma20_display}\n"
            section += f"  • Support : {support_display}\n"
            section += f"  • Résistance : {resistance_display}\n\n"
        else:
            section += "Indicateurs techniques indisponibles.\n\n"
        
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
        if market.fear_greed_index is not None:
            section += f"😱 Fear & Greed Index : {market.fear_greed_index}/100\n\n"

        return section
    
    def _generate_comparison_section(self, markets_data: Dict[str, MarketData],
                                    opportunities: Dict[str, OpportunityScore]) -> str:
        """Section comparative"""
        
        section = "📊 COMPARAISON\n"
        section += "-" * 70 + "\n\n"

        if not markets_data:
            section += "Aucune donnée de marché disponible.\n\n"
            return section

        # Tableau comparatif
        section += f"{'Symbole':<10} {'Prix':<16} {'24h':<12} {'RSI':<10} {'Score':<8}\n"
        section += "-" * 70 + "\n"

        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            opp = opportunities.get(symbol)

            price_text = self._format_price(market)
            change_text = self._format_change(market)
            rsi_value = self._format_rsi(market)
            score_text = f"{opp.score}/10" if opp else "N/A"

            section += f"{symbol:<10} {price_text:<16} {change_text:<12} {rsi_value:<10} {score_text:<8}\n"
        
        section += "\n"
        return section
    
    def _generate_recommendations(self, markets_data: Dict[str, MarketData],
                                 opportunities: Dict[str, OpportunityScore]) -> str:
        """Recommandations"""

        section = "💡 RECOMMANDATIONS\n"
        section += "-" * 70 + "\n\n"

        if not opportunities:
            section += "Aucune opportunité analysée pour le moment.\n\n"
            return section

        # Trier par score d'opportunité
        sorted_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)

        # Achats recommandés
        section += "À acheter maintenant :\n"
        buy_recommendations = [item for item in sorted_opps if item[1].score >= 7]

        if buy_recommendations:
            for symbol, opp in buy_recommendations:
                market = markets_data.get(symbol)
                section += f"  ✅ {symbol} à {self._format_price(market)} "
                section += f"(Score: {opp.score}/10)\n"
        else:
            section += "  Aucune opportunité excellente actuellement\n"

        section += "\n"

        # À surveiller
        section += "À surveiller :\n"
        watch_recommendations = [item for item in sorted_opps if 5 <= item[1].score < 7]

        if watch_recommendations:
            for symbol, opp in watch_recommendations[:3]:
                market = markets_data.get(symbol)
                section += f"  👀 {symbol} à {self._format_price(market)} "
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

    @staticmethod
    def _format_price(market: Optional[MarketData]) -> str:
        """Retourne une représentation textuelle robuste du prix."""

        if not market or not market.current_price or market.current_price.price_eur is None:
            return "prix indisponible"

        return f"{market.current_price.price_eur:.2f}€"

    @staticmethod
    def _format_change(market: Optional[MarketData]) -> str:
        if not market or not market.current_price:
            return "indisponible"

        change = market.current_price.change_24h
        if change is None:
            return "indisponible"

        return f"{change:+.2f}%"

    @staticmethod
    def _format_volume(market: Optional[MarketData]) -> str:
        if not market or not market.current_price:
            return "indisponible"

        volume = market.current_price.volume_24h
        if volume is None:
            return "indisponible"

        return f"{volume:,.0f}"

    @staticmethod
    def _format_rsi(market: Optional[MarketData]) -> str:
        if not market or not market.technical_indicators:
            return "indisponible"

        rsi = market.technical_indicators.rsi
        if rsi is None:
            return "indisponible"

        return f"{rsi:.0f}"

    @staticmethod
    def _collect_valid_changes(markets_data: Dict[str, MarketData]) -> List[float]:
        """Retourne toutes les variations 24h disponibles."""

        changes: List[float] = []
        for market in markets_data.values():
            if not market or not market.current_price:
                continue

            change = market.current_price.change_24h
            if change is not None:
                changes.append(change)

        return changes

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
