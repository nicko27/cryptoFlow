"""
Service de suggestions d'investissement
Propose d'autres cryptos intéressantes basé sur analyse multi-critères
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from core.models import MarketData, OpportunityScore, Prediction


@dataclass
class InvestmentSuggestion:
    """Suggestion d'investissement dans une autre crypto"""
    symbol: str
    score: float  # Score global 0-10
    opportunity_score: Optional[int] = None
    current_price: float = 0.0
    change_24h: float = 0.0
    
    # Raisons de la suggestion
    reasons: List[str] = None
    primary_reason: str = ""
    
    # Niveau de risque
    risk_level: str = "medium"  # low, medium, high
    
    # Message personnalisé
    kid_friendly_message: str = ""
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class InvestmentSuggestionService:
    """Service de génération de suggestions d'investissement"""
    
    def __init__(self):
        self.emoji_map = {
            "strong_trend": "📈",
            "undervalued": "💎",
            "high_volume": "🔥",
            "good_prediction": "🎯",
            "low_volatility": "🛡️",
            "momentum": "🚀",
            "recovery": "🌱"
        }
    
    def generate_suggestions(
        self,
        current_symbol: str,
        all_market_data: Dict[str, MarketData],
        all_predictions: Dict[str, Prediction],
        all_opportunities: Dict[str, OpportunityScore],
        max_suggestions: int = 3,
        min_opportunity_score: int = 7,
        exclude_current: bool = True,
        prefer_low_volatility: bool = False,
        prefer_trending: bool = True,
        prefer_undervalued: bool = True,
        excluded_symbols: Optional[List[str]] = None,
    ) -> List[InvestmentSuggestion]:
        """
        Génère des suggestions d'investissement
        
        Args:
            current_symbol: Symbole de la crypto actuelle
            all_market_data: Données marché de toutes les cryptos
            all_predictions: Prédictions de toutes les cryptos
            all_opportunities: Scores d'opportunité de toutes les cryptos
            max_suggestions: Nombre maximum de suggestions
            min_opportunity_score: Score minimum pour suggérer
            exclude_current: Exclure la crypto actuelle
            prefer_low_volatility: Privilégier les cryptos stables
            prefer_trending: Privilégier les cryptos en tendance
            prefer_undervalued: Privilégier les cryptos sous-évaluées
        """
        suggestions = []
        excluded = {s.upper() for s in (excluded_symbols or [])}
        if exclude_current:
            excluded.add(current_symbol.upper())
        
        # Parcourir toutes les cryptos disponibles
        for symbol in all_market_data.keys():
            if symbol.upper() in excluded:
                continue
            
            market = all_market_data.get(symbol)
            prediction = all_predictions.get(symbol)
            opportunity = all_opportunities.get(symbol)
            
            # Vérifier que nous avons les données nécessaires
            if not market or not opportunity:
                continue
            
            # Filtrer par score d'opportunité minimum
            if opportunity.score < min_opportunity_score:
                continue
            
            # Calculer le score de suggestion
            suggestion = self._evaluate_suggestion(
                symbol=symbol,
                market=market,
                prediction=prediction,
                opportunity=opportunity,
                prefer_low_volatility=prefer_low_volatility,
                prefer_trending=prefer_trending,
                prefer_undervalued=prefer_undervalued,
            )
            
            if suggestion and suggestion.score > 0:
                suggestions.append(suggestion)
        
        # Trier par score décroissant
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        # Limiter au nombre demandé
        return suggestions[:max_suggestions]
    
    def _evaluate_suggestion(
        self,
        symbol: str,
        market: MarketData,
        prediction: Optional[Prediction],
        opportunity: OpportunityScore,
        prefer_low_volatility: bool,
        prefer_trending: bool,
        prefer_undervalued: bool,
    ) -> Optional[InvestmentSuggestion]:
        """Évalue une crypto et génère une suggestion si pertinent"""
        
        score_factors = []
        reasons = []
        risk_level = "medium"
        
        # Score de base = score d'opportunité normalisé
        base_score = opportunity.score / 10.0
        score_factors.append(("base", base_score))
        
        # Facteur 1: Tendance haussière forte
        if prefer_trending and market.price_change_24h and market.price_change_24h > 3.0:
            bonus = min(market.price_change_24h / 20.0, 0.3)  # Max +0.3
            score_factors.append(("trending", bonus))
            reasons.append("strong_trend")
            if market.price_change_24h > 10:
                risk_level = "high"
        
        # Facteur 2: Prix attractif (baisse récente = opportunité d'achat)
        if prefer_undervalued and market.price_change_24h and -5.0 < market.price_change_24h < -1.0:
            bonus = abs(market.price_change_24h) / 20.0  # Max +0.25
            score_factors.append(("undervalued", bonus))
            reasons.append("undervalued")
            risk_level = "low"
        
        # Facteur 3: Volume élevé (liquidité importante)
        if market.volume_24h and market.market_cap:
            volume_ratio = market.volume_24h / market.market_cap if market.market_cap > 0 else 0
            if volume_ratio > 0.1:  # Volume > 10% de la market cap
                bonus = min(volume_ratio * 2, 0.2)  # Max +0.2
                score_factors.append(("volume", bonus))
                reasons.append("high_volume")
        
        # Facteur 4: Prédiction IA positive
        if prediction and prediction.prediction_type.value == "HAUSSIER":
            confidence_bonus = (prediction.confidence / 100.0) * 0.25  # Max +0.25
            score_factors.append(("prediction", confidence_bonus))
            reasons.append("good_prediction")
        
        # Facteur 5: Faible volatilité (si préféré)
        if prefer_low_volatility and market.price_change_24h:
            if abs(market.price_change_24h) < 2.0:  # Variation < 2%
                score_factors.append(("stability", 0.15))
                reasons.append("low_volatility")
                risk_level = "low"
        
        # Facteur 6: Momentum positif (7j)
        if market.price_change_7d and market.price_change_7d > 5.0:
            momentum_bonus = min(market.price_change_7d / 50.0, 0.2)  # Max +0.2
            score_factors.append(("momentum", momentum_bonus))
            reasons.append("momentum")
        
        # Facteur 7: Recovery (remontée après baisse)
        if market.price_change_24h and market.price_change_7d:
            if market.price_change_24h > 2.0 and market.price_change_7d < -5.0:
                score_factors.append(("recovery", 0.15))
                reasons.append("recovery")
        
        # Calculer score final
        final_score = sum(factor[1] for factor in score_factors)
        final_score = min(final_score * 10, 10.0)  # Normaliser sur 10
        
        # Ne suggérer que si score > 6
        if final_score < 6.0:
            return None
        
        # Identifier raison principale (facteur le plus important)
        if len(score_factors) > 1:
            primary_factor = max(score_factors[1:], key=lambda x: x[1])[0]
            primary_reason = self._get_reason_from_factor(primary_factor)
        else:
            primary_reason = "bonne opportunité générale"
        
        # Créer message convivial
        kid_message = self._create_kid_friendly_message(
            symbol=symbol,
            reasons=reasons,
            score=final_score,
            market=market,
        )
        
        return InvestmentSuggestion(
            symbol=symbol,
            score=final_score,
            opportunity_score=opportunity.score,
            current_price=market.current_price.price_eur if market.current_price else 0,
            change_24h=market.price_change_24h or 0,
            reasons=reasons,
            primary_reason=primary_reason,
            risk_level=risk_level,
            kid_friendly_message=kid_message,
        )
    
    def _get_reason_from_factor(self, factor: str) -> str:
        """Convertit un facteur en raison lisible"""
        reason_map = {
            "trending": "forte tendance haussière",
            "undervalued": "prix attractif pour acheter",
            "volume": "beaucoup d'activité (liquidité)",
            "prediction": "prédiction IA très positive",
            "stability": "crypto stable et sûre",
            "momentum": "belle dynamique de hausse",
            "recovery": "en train de remonter",
            "base": "bonne opportunité",
        }
        return reason_map.get(factor, "opportunité intéressante")
    
    def _create_kid_friendly_message(
        self,
        symbol: str,
        reasons: List[str],
        score: float,
        market: MarketData,
    ) -> str:
        """Crée un message clair et motivant pour l'utilisateur.

        On inclut prix actuel, variation récente, et un prix d'entrée conseillé.
        """
        lines = [
            f"Je lui donne {score:.1f}/10 parce que {self._summarize_primary_reason(reasons)}.",
            "Ce qui ressort :",
        ]

        reason_map = {
            "strong_trend": "La tendance est très haussière, le marché est enthousiaste 📈",
            "undervalued": "Le prix semble attractif par rapport aux récents niveaux 💎",
            "high_volume": "Il y a beaucoup d'échanges, donc tu peux acheter/vendre facilement 🔥",
            "good_prediction": "L'IA prévoit une poursuite de la hausse 🎯",
            "low_volatility": "Le prix bouge doucement, pratique pour accumuler sereinement 🛡️",
            "momentum": "La dynamique sur plusieurs jours est très positive 🚀",
            "recovery": "Elle se reprend après une baisse, signe de rebond 🌱",
        }

        detailed_reasons = [
            f"• {reason_map[key]}"
            for key in reasons
            if key in reason_map
        ]
        lines.extend(detailed_reasons or ["• C'est une opportunité solide à surveiller 👀"])

        return "\n".join(lines)

    def _summarize_primary_reason(self, reasons: List[str]) -> str:
        """Résumé en une phrase lisible de la principale raison."""
        reason_order = [
            "strong_trend",
            "undervalued",
            "good_prediction",
            "high_volume",
            "momentum",
            "recovery",
            "low_volatility",
        ]
        descriptions = {
            "strong_trend": "elle est en pleine forme",
            "undervalued": "le prix est intéressant",
            "good_prediction": "l'IA est confiante",
            "high_volume": "la liquidité est très forte",
            "momentum": "le mouvement reste puissant",
            "recovery": "elle rebondit et reprend de la force",
            "low_volatility": "elle est stable et rassurante",
        }
        for key in reason_order:
            if key in reasons:
                return descriptions.get(key, "c'est une opportunité solide")
        return "c'est une opportunité solide"
    
    def format_suggestions_message(
        self,
        suggestions: List[InvestmentSuggestion],
        kid_friendly: bool = True,
        use_emojis: bool = True,
    ) -> str:
        """Formate les suggestions en message Telegram"""
        
        if not suggestions:
            return ""
        
        lines = []
        
        # En-tête
        if kid_friendly:
            lines.append("💡 D'autres cryptos qui pourraient t'intéresser :")
        else:
            lines.append("💡 Suggestions d'investissement :")
        
        lines.append("")
        
        # Chaque suggestion
        for i, suggestion in enumerate(suggestions, 1):
            # Emoji selon niveau de risque
            risk_emoji = {
                "low": "🛡️",
                "medium": "⚖️",
                "high": "⚠️"
            }.get(suggestion.risk_level, "")
            
            # Emoji de la raison principale
            reason_emoji = ""
            for reason_key, emoji in self.emoji_map.items():
                if reason_key in suggestion.reasons:
                    reason_emoji = emoji
                    break
            
            if kid_friendly:
                lines.append(f"{i}. {reason_emoji} {suggestion.symbol} ({suggestion.score:.1f}/10 {risk_emoji})")
                lines.append(f"   Prix actuel : {suggestion.current_price:.2f}€ ({suggestion.change_24h:+.1f}% /24h)")
                entry_price = max(suggestion.current_price * 0.98, 0.0)
                lines.append(f"   Prix d'achat conseillé : {entry_price:.2f}€")
                lines.append("   " + suggestion.kid_friendly_message.replace("\n", "\n   "))
            else:
                lines.append(
                    f"{i}. {reason_emoji} **{suggestion.symbol}** - "
                    f"Score {suggestion.score:.1f}/10 {risk_emoji}"
                )
                lines.append(f"   Prix: {suggestion.current_price:.2f}€ ({suggestion.change_24h:+.1f}% 24h)")
                lines.append(f"   Raison: {suggestion.primary_reason}")
            
            lines.append("")
        
        # Pied de page
        if kid_friendly:
            lines.append("ℹ️ Ce sont juste des idées, pas des ordres ! Demande toujours à un adulte avant d'investir.")
        
        return "\n".join(lines)
    
    def get_diversification_suggestions(
        self,
        current_portfolio: List[str],
        all_market_data: Dict[str, MarketData],
        all_predictions: Dict[str, Prediction],
        all_opportunities: Dict[str, OpportunityScore],
        max_suggestions: int = 3,
    ) -> List[InvestmentSuggestion]:
        """
        Suggère des cryptos pour diversifier le portfolio
        Exclut les cryptos déjà possédées
        """
        suggestions = []
        
        for symbol in all_market_data.keys():
            if symbol in current_portfolio:
                continue
            
            market = all_market_data.get(symbol)
            prediction = all_predictions.get(symbol)
            opportunity = all_opportunities.get(symbol)
            
            if not market or not opportunity or opportunity.score < 6:
                continue
            
            # Favoriser la diversification: chercher des cryptos différentes
            suggestion = self._evaluate_suggestion(
                symbol=symbol,
                market=market,
                prediction=prediction,
                opportunity=opportunity,
                prefer_low_volatility=True,  # Privilégier stabilité pour diversification
                prefer_trending=True,
                prefer_undervalued=True,
            )
            
            if suggestion:
                suggestions.append(suggestion)
        
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:max_suggestions]
