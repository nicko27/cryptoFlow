"""
Summary Service - Génération de résumés automatiques
"""

from typing import Dict, Optional
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
        has_market_data = bool(markets_data)

        # Meilleure opportunité
        if opportunities:
            best_symbol, best_opportunity = max(opportunities.items(), key=lambda x: x[1].score)
            msg += "🎯 <b>MEILLEURE OPPORTUNITÉ</b>\n"

            if best_opportunity.score < 7:
                msg += "Aucune opportunité forte détectée pour le moment.\n\n"
            else:
                market = markets_data.get(best_symbol) if has_market_data else None
                price_text = self._format_price_for_summary(market)
                msg += f"{best_symbol}: {price_text}\n"

                change_24h = self._get_change_value(market)
                change_7d = self._get_weekly_change_value(market)

                trend_line = self._format_trend_details(change_24h, change_7d)
                if trend_line:
                    msg += f"{trend_line}\n"

                recommendation_line = self._trend_recommendation(change_24h, change_7d)
                if recommendation_line:
                    msg += f"{recommendation_line}\n"

                msg += f"Score: {best_opportunity.score}/10 ⭐\n"
                msg += f"{best_opportunity.recommendation}\n\n"
        else:
            msg += "Aucune opportunité identifiée pour le moment.\n\n"

        if not has_market_data:
            msg += "Aucune donnée de marché disponible pour le moment.\n"
            msg += f"\n🕒 Prochain résumé à {self._next_summary_time()}"
            return msg

        if self.config.telegram_show_prices:
            msg += "<b>Prix actuels:</b>\n"
            for symbol in sorted(markets_data.keys()):
                market = markets_data[symbol]
                price = self._get_price_value(market)
                change_24h = self._get_change_value(market)
                change_7d = self._get_weekly_change_value(market)

                if price is None:
                    msg += f"⚪ {symbol}: prix indisponible\n"
                    continue

                emoji = "⚪"
                if change_24h is not None:
                    emoji = "📈" if change_24h > 0 else "📉"

                line = f"{emoji} {symbol}: {price:.2f}€"

                trend_line = self._format_trend_details(change_24h, change_7d)
                if trend_line:
                    line += f" | {trend_line}"

                recommendation_line = self._trend_recommendation(change_24h, change_7d)
                if recommendation_line:
                    line += f" → {recommendation_line}"

                msg += f"{line}\n"

        msg += f"\n🕒 Prochain résumé à {self._next_summary_time()}"

        return msg
    
    def _generate_detailed_summary(self, 
                                   markets_data: Dict[str, MarketData],
                                   predictions: Dict[str, Prediction],
                                   opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé détaillé"""
        
        msg = f"📊 <b>RÉSUMÉ DÉTAILLÉ - {datetime.now().strftime('%d/%m %H:%M')}</b>\n\n"

        has_market_data = bool(markets_data)

        # Vue d'ensemble
        msg += "<b>🌍 VUE D'ENSEMBLE</b>\n"

        if has_market_data:
            change_lines = []

            if self.config.telegram_show_trend_24h:
                changes = [self._get_change_value(m) for m in markets_data.values()]
                valid_changes = [c for c in changes if c is not None]

                if valid_changes:
                    avg_change = sum(valid_changes) / len(valid_changes)
                    trend_emoji = "📈" if avg_change > 0 else "📉"
                    change_lines.append(f"{trend_emoji} 24h: {avg_change:+.2f}%")
                else:
                    change_lines.append("24h: données indisponibles")

            if self.config.telegram_show_trend_7d:
                weekly_changes = [self._get_weekly_change_value(m) for m in markets_data.values()]
                valid_weekly = [c for c in weekly_changes if c is not None]

                if valid_weekly:
                    avg_weekly = sum(valid_weekly) / len(valid_weekly)
                    weekly_emoji = "🚀" if avg_weekly > 0 else "📉"
                    change_lines.append(f"{weekly_emoji} 7j: {avg_weekly:+.2f}%")
                else:
                    change_lines.append("7j: données indisponibles")

            if change_lines:
                msg += " | ".join(change_lines) + "\n\n"
            else:
                msg += "ℹ️ Tendance globale: données indisponibles\n\n"
        else:
            msg += "Données de marché indisponibles pour le moment.\n"
            msg += "Nous conservons néanmoins les meilleures opportunités identifiées.\n\n"

        # Meilleures opportunités
        sorted_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)

        msg += "<b>⭐ TOP OPPORTUNITÉS</b>\n"
        if not sorted_opps:
            msg += "Aucune opportunité analysée pour le moment.\n"
        for symbol, opp in sorted_opps[:3]:
            market = markets_data.get(symbol) if has_market_data else None
            pred = predictions.get(symbol)

            msg += f"\n<b>{symbol}</b> - Score {opp.score}/10\n"

            price = self._get_price_value(market)
            change = self._get_change_value(market) if market else None
            weekly_change = self._get_weekly_change_value(market) if market else None

            if price is not None:
                msg += f"Prix: {price:.2f}€\n"
                trend_line = self._format_trend_details(change, weekly_change)
                if trend_line:
                    msg += f"Tendance: {trend_line}\n"
            else:
                msg += "Prix: données indisponibles\n"
                if change is not None and self.config.telegram_show_trend_24h:
                    msg += f"Variation 24h: {change:+.1f}%\n"
                elif self.config.telegram_show_trend_24h:
                    msg += "Variation 24h: indisponible\n"

                if weekly_change is not None and self.config.telegram_show_trend_7d:
                    msg += f"Variation 7j: {weekly_change:+.1f}%\n"
                elif self.config.telegram_show_trend_7d:
                    msg += "Variation 7j: indisponible\n"

            if price is not None and change is None:
                if self.config.telegram_show_trend_24h:
                    msg += "Variation 24h: indisponible\n"

            recommendation_line = self._trend_recommendation(change, weekly_change)
            if recommendation_line:
                msg += f"Recommandation: {recommendation_line}\n"

            if pred:
                msg += f"Prédiction: {pred.direction} {pred.prediction_type.value}\n"

            rsi = self._get_rsi_value(market)
            if rsi is not None:
                msg += f"RSI: {rsi:.0f}\n"
            else:
                msg += "RSI: indisponible\n"
        
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
        else:
            msg += "\n<b>😱 Fear & Greed:</b> données indisponibles\n"
        
        msg += f"\n🕒 Prochain résumé: {self._next_summary_time()}"
        
        return msg
    
    def _next_summary_time(self) -> str:
        """Calcule l'heure du prochain résumé"""
        current_hour = datetime.now().hour
        
        # Trouver la prochaine heure de résumé
        if not self.config.summary_hours:
            return "indisponible"

        next_hours = [h for h in self.config.summary_hours if h > current_hour]

        if next_hours:
            return f"{next_hours[0]}:00"
        else:
            return f"{self.config.summary_hours[0]}:00 (demain)"
    
    def generate_morning_summary(self, markets_data: Dict[str, MarketData],
                                opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé spécial du matin"""
        
        msg = "☀️ <b>BONJOUR - RÉSUMÉ DU MATIN</b>\n\n"

        has_market_data = bool(markets_data)

        if opportunities:
            best_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)[:2]
            msg += "<b>🎯 OPPORTUNITÉS DU JOUR</b>\n"
            for symbol, opp in best_opps:
                msg += f"\n{symbol}: {opp.score}/10 ⭐\n"
                market = markets_data.get(symbol) if has_market_data else None
                price = self._get_price_value(market)
                if price is not None:
                    msg += f"Prix: {price:.2f}€\n"
                else:
                    msg += "Prix: données indisponibles\n"
                msg += f"{opp.recommendation}\n"
        else:
            msg += "Aucune opportunité détectée pour le moment.\n"

        # Changements nocturnes
        msg += "\n<b>📊 CHANGEMENTS 24H</b>\n"
        if not has_market_data:
            msg += "Données de marché indisponibles pour le moment.\n"
            msg += "\n<i>Bonne journée de trading ! 🚀</i>"
            return msg

        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            change = self._get_change_value(market)

            if change is None:
                msg += f"⚪ {symbol}: variation indisponible\n"
                continue

            emoji = "🟢" if change > 0 else "🔴"
            msg += f"{emoji} {symbol}: {change:+.1f}%\n"

        msg += "\n<i>Bonne journée de trading ! 🚀</i>"

        return msg
    
    def generate_evening_summary(self, markets_data: Dict[str, MarketData],
                                opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé spécial du soir"""
        
        msg = "🌙 <b>RÉSUMÉ DU SOIR</b>\n\n"

        has_market_data = bool(markets_data)

        # Bilan de la journée
        msg += "<b>📈 BILAN DE LA JOURNÉE</b>\n"

        if has_market_data:
            gainers = []
            losers = []

            for symbol, market in markets_data.items():
                change = self._get_change_value(market)
                if change is None:
                    continue
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

            if not gainers and not losers:
                msg += "\nAucune variation disponible pour le moment.\n"
        else:
            msg += "Données de marché indisponibles pour le moment.\n"

        # Opportunités pour demain
        if opportunities:
            best_opp = max(opportunities.items(), key=lambda x: x[1].score)
            if best_opp[1].score >= 6:
                msg += f"\n<b>💡 OPPORTUNITÉ POUR DEMAIN</b>\n"
                msg += f"{best_opp[0]} - Score {best_opp[1].score}/10\n"
                msg += f"{best_opp[1].recommendation}\n"
            else:
                msg += "\nAucune opportunité forte identifiée pour demain.\n"
        else:
            msg += "\nAucune opportunité identifiée pour demain.\n"

        msg += "\n<i>Bonne soirée ! 🌟</i>"

        return msg

    @staticmethod
    def _get_price_value(market: Optional[MarketData]) -> Optional[float]:
        if not market or not market.current_price:
            return None

        price = market.current_price.price_eur
        return price if price is not None else None

    @staticmethod
    def _get_change_value(market: Optional[MarketData]) -> Optional[float]:
        if not market or not market.current_price:
            return None

        change = market.current_price.change_24h
        return change if change is not None else None

    @staticmethod
    def _get_weekly_change_value(market: Optional[MarketData]) -> Optional[float]:
        if not market:
            return None

        weekly = getattr(market, "weekly_change", None)
        return weekly if weekly is not None else None

    @staticmethod
    def _get_rsi_value(market: Optional[MarketData]) -> Optional[float]:
        if not market or not market.technical_indicators:
            return None

        rsi = market.technical_indicators.rsi
        return rsi if rsi is not None else None

    def _format_price_for_summary(self, market: Optional[MarketData]) -> str:
        price = self._get_price_value(market)
        if price is not None:
            return f"{price:.2f}€"
        return "données de prix indisponibles"

    def _format_trend_details(self,
                              change_24h: Optional[float],
                              change_7d: Optional[float]) -> str:
        parts = []

        if self.config.telegram_show_trend_24h:
            if change_24h is None:
                parts.append("24h: variation indisponible")
            else:
                parts.append(f"24h: {change_24h:+.1f}%")

        if self.config.telegram_show_trend_7d:
            if change_7d is None:
                parts.append("7j: variation indisponible")
            else:
                parts.append(f"7j: {change_7d:+.1f}%")

        return " | ".join(parts)

    def _trend_recommendation(self,
                              change_24h: Optional[float],
                              change_7d: Optional[float]) -> str:
        if not self.config.telegram_show_recommendations:
            return ""

        buy_signal = False
        sell_signal = False

        if change_24h is None and change_7d is None:
            return ""

        if change_24h is not None:
            if change_24h >= self.config.trend_buy_threshold_24h:
                buy_signal = True
            if change_24h <= self.config.trend_sell_threshold_24h:
                sell_signal = True

        if change_7d is not None:
            if change_7d >= self.config.trend_buy_threshold_7d:
                buy_signal = True
            if change_7d <= self.config.trend_sell_threshold_7d:
                sell_signal = True

        if buy_signal and sell_signal:
            return "🤔 Signal mixte — surveiller le marché"
        if buy_signal:
            return "✅ Tendance haussière — opportunité d'achat"
        if sell_signal:
            return "⚠️ Tendance baissière — envisager de vendre"

        return "⏳ Aucun signal clair"
