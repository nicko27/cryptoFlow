"""
Summary Service - Génération de résumés automatiques
"""

from typing import Dict, List
from datetime import datetime, time as dt_time
from core.models import MarketData, Prediction, OpportunityScore, BotConfiguration


class SummaryService:
    """Service de génération de résumés automatiques"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.last_summary_hour = None
    
    def should_send_summary(self) -> bool:
        """Détermine s'il faut envoyer un résumé"""
        current_hour = datetime.now().hour
        
        # Vérifier si c'est une heure de résumé configurée
        if current_hour not in self.config.summary_hours:
            return False
        
        # Éviter d'envoyer plusieurs fois dans la même heure
        if self.last_summary_hour == current_hour:
            return False
        
        # Vérifier mode nuit
        if self.config.enable_quiet_hours:
            if self._is_quiet_hours():
                return False
        
        self.last_summary_hour = current_hour
        return True
    
    def _is_quiet_hours(self) -> bool:
        """Vérifie si on est en heures silencieuses"""
        current_hour = datetime.now().hour
        start = self.config.quiet_start_hour
        end = self.config.quiet_end_hour
        
        if start < end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end
    
    def generate_summary(self, 
                        markets_data: Dict[str, MarketData],
                        predictions: Dict[str, Prediction],
                        opportunities: Dict[str, OpportunityScore],
                        simple: bool = False) -> str:
        """Génère un résumé complet"""
        
        if simple:
            return self._generate_simple_summary(markets_data, opportunities)
        else:
            return self._generate_detailed_summary(markets_data, predictions, opportunities)
    
    def _generate_simple_summary(self, markets_data: Dict[str, MarketData],
                                 opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé simple et clair"""
        
        msg = f"📊 <b>RÉSUMÉ {datetime.now().strftime('%H:%M')}</b>\n\n"
        
        # Meilleure opportunité
        best = max(opportunities.items(), key=lambda x: x[1].score)
        if best[1].score >= 7:
            price = markets_data[best[0]].current_price.price_eur
            msg += f"🎯 <b>MEILLEURE OPPORTUNITÉ</b>\n"
            msg += f"{best[0]} à {price:.2f}€\n"
            msg += f"Score: {best[1].score}/10 ⭐\n"
            msg += f"{best[1].recommendation}\n\n"
        
        # Prix de toutes les cryptos
        msg += "<b>Prix actuels:</b>\n"
        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            price = market.current_price.price_eur
            change = market.current_price.change_24h
            emoji = "📈" if change > 0 else "📉"
            
            msg += f"{emoji} {symbol}: {price:.2f}€ ({change:+.1f}%)\n"
        
        msg += f"\n🕒 Prochain résumé à {self._next_summary_time()}"
        
        return msg
    
    def _generate_detailed_summary(self, 
                                   markets_data: Dict[str, MarketData],
                                   predictions: Dict[str, Prediction],
                                   opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé détaillé"""
        
        msg = f"📊 <b>RÉSUMÉ DÉTAILLÉ - {datetime.now().strftime('%d/%m %H:%M')}</b>\n\n"
        
        # Vue d'ensemble
        msg += "<b>🌍 VUE D'ENSEMBLE</b>\n"
        
        avg_change = sum(m.current_price.change_24h for m in markets_data.values()) / len(markets_data)
        trend_emoji = "📈" if avg_change > 0 else "📉"
        msg += f"{trend_emoji} Tendance globale: {avg_change:+.2f}%\n\n"
        
        # Meilleures opportunités
        sorted_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)
        
        msg += "<b>⭐ TOP OPPORTUNITÉS</b>\n"
        for symbol, opp in sorted_opps[:3]:
            market = markets_data[symbol]
            pred = predictions.get(symbol)
            
            msg += f"\n<b>{symbol}</b> - Score {opp.score}/10\n"
            msg += f"Prix: {market.current_price.price_eur:.2f}€ "
            msg += f"({market.current_price.change_24h:+.1f}%)\n"
            
            if pred:
                msg += f"Prédiction: {pred.direction} {pred.prediction_type.value}\n"
            
            msg += f"RSI: {market.technical_indicators.rsi:.0f}\n"
        
        # À éviter
        to_avoid = [item for item in sorted_opps if item[1].score < 5]
        if to_avoid:
            msg += "\n<b>⚠️ À ÉVITER</b>\n"
            for symbol, opp in to_avoid:
                msg += f"• {symbol} (Score: {opp.score}/10)\n"
        
        # Fear & Greed
        fgi_values = [m.fear_greed_index for m in markets_data.values() 
                     if m.fear_greed_index is not None]
        if fgi_values:
            avg_fgi = sum(fgi_values) / len(fgi_values)
            msg += f"\n<b>😱 Fear & Greed: {int(avg_fgi)}/100</b>\n"
            
            if avg_fgi < 30:
                msg += "Peur extrême - Opportunité d'achat\n"
            elif avg_fgi > 70:
                msg += "Avidité extrême - Prudence recommandée\n"
        
        msg += f"\n🕒 Prochain résumé: {self._next_summary_time()}"
        
        return msg
    
    def _next_summary_time(self) -> str:
        """Calcule l'heure du prochain résumé"""
        current_hour = datetime.now().hour
        
        # Trouver la prochaine heure de résumé
        next_hours = [h for h in self.config.summary_hours if h > current_hour]
        
        if next_hours:
            return f"{next_hours[0]}:00"
        else:
            return f"{self.config.summary_hours[0]}:00 (demain)"
    
    def generate_morning_summary(self, markets_data: Dict[str, MarketData],
                                opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé spécial du matin"""
        
        msg = "☀️ <b>BONJOUR - RÉSUMÉ DU MATIN</b>\n\n"
        
        # Opportunités du jour
        best_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)[:2]
        
        msg += "<b>🎯 OPPORTUNITÉS DU JOUR</b>\n"
        for symbol, opp in best_opps:
            market = markets_data[symbol]
            msg += f"\n{symbol}: {opp.score}/10 ⭐\n"
            msg += f"Prix: {market.current_price.price_eur:.2f}€\n"
            msg += f"{opp.recommendation}\n"
        
        # Changements nocturnes
        msg += "\n<b>📊 CHANGEMENTS 24H</b>\n"
        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            change = market.current_price.change_24h
            emoji = "🟢" if change > 0 else "🔴"
            msg += f"{emoji} {symbol}: {change:+.1f}%\n"
        
        msg += "\n<i>Bonne journée de trading ! 🚀</i>"
        
        return msg
    
    def generate_evening_summary(self, markets_data: Dict[str, MarketData],
                                opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé spécial du soir"""
        
        msg = "🌙 <b>RÉSUMÉ DU SOIR</b>\n\n"
        
        # Bilan de la journée
        msg += "<b>📈 BILAN DE LA JOURNÉE</b>\n"
        
        gainers = []
        losers = []
        
        for symbol, market in markets_data.items():
            change = market.current_price.change_24h
            if change > 0:
                gainers.append((symbol, change))
            else:
                losers.append((symbol, change))
        
        if gainers:
            gainers.sort(key=lambda x: x[1], reverse=True)
            msg += "\n🟢 Meilleurs performances:\n"
            for symbol, change in gainers[:3]:
                msg += f"  • {symbol}: +{change:.1f}%\n"
        
        if losers:
            losers.sort(key=lambda x: x[1])
            msg += "\n🔴 Plus grosses baisses:\n"
            for symbol, change in losers[:3]:
                msg += f"  • {symbol}: {change:.1f}%\n"
        
        # Opportunités pour demain
        best_opp = max(opportunities.items(), key=lambda x: x[1].score)
        if best_opp[1].score >= 6:
            msg += f"\n<b>💡 OPPORTUNITÉ POUR DEMAIN</b>\n"
            msg += f"{best_opp[0]} - Score {best_opp[1].score}/10\n"
            msg += f"{best_opp[1].recommendation}\n"
        
        msg += "\n<i>Bonne soirée ! 🌟</i>"
        
        return msg
