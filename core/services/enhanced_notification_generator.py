"""
Service de génération de notifications amélioré
Utilise le nouveau système de configuration ultra-paramétrable
"""

from datetime import datetime
from typing import Optional, Dict, List
from core.models import MarketData, Prediction, OpportunityScore
from core.models.notification_config import (
    GlobalNotificationSettings,
    ScheduledNotificationConfig,
    CoinNotificationProfile,
    PriceBlock, PredictionBlock, OpportunityBlock,
    ChartBlock, BrokersBlock, FearGreedBlock,
    GainLossBlock, InvestmentSuggestionBlock, GlossaryBlock
)
from core.services.investment_suggestion_service import InvestmentSuggestionService


class EnhancedNotificationGenerator:
    """Générateur de notifications avancé et paramétrable"""
    
    def __init__(self, settings: GlobalNotificationSettings):
        self.settings = settings
        self.suggestion_service = InvestmentSuggestionService()
        
        # Termes détectés dans le message pour le glossaire automatique
        self.detected_terms = set()
    
    def generate_notification(
        self,
        symbol: str,
        market: MarketData,
        prediction: Optional[Prediction],
        opportunity: Optional[OpportunityScore],
        all_markets: Dict[str, MarketData],
        all_predictions: Dict[str, Prediction],
        all_opportunities: Dict[str, OpportunityScore],
        current_hour: int,
        current_day_of_week: int,
    ) -> Optional[str]:
        """
        Génère une notification complète pour une crypto
        
        Returns:
            Le message de notification ou None si pas de notification à envoyer
        """
        
        # Vérifier si les notifications sont activées globalement
        if not self.settings.enabled:
            return None
        
        # Récupérer le profil de la crypto
        profile = self.settings.get_coin_profile(symbol)
        if not profile.enabled:
            return None
        
        # Vérifier si on est dans les heures silencieuses
        if self._is_quiet_hour(current_hour):
            return None
        
        # Récupérer la configuration active pour cette heure
        config = profile.get_active_config(current_hour, current_day_of_week)
        if not config or not config.enabled:
            return None
        
        # Vérifier les seuils d'envoi
        if not self._should_send(config, market, opportunity):
            return None
        
        # Réinitialiser les termes détectés
        self.detected_terms.clear()
        
        # Construire le message
        message_parts = []
        
        # Header
        header = self._generate_header(symbol, config, current_hour)
        if header:
            message_parts.append(header)
        
        # Intro personnalisée du profil
        if profile.intro_message:
            message_parts.append(profile.intro_message)
        
        # Générer chaque bloc selon l'ordre configuré
        for block_name in config.blocks_order:
            block_content = self._generate_block(
                block_name=block_name,
                config=config,
                symbol=symbol,
                market=market,
                prediction=prediction,
                opportunity=opportunity,
                all_markets=all_markets,
                all_predictions=all_predictions,
                all_opportunities=all_opportunities,
            )
            
            if block_content:
                message_parts.append(block_content)
        
        # Outro personnalisée du profil
        if profile.outro_message:
            message_parts.append(profile.outro_message)
        
        # Footer
        footer = self._generate_footer(config)
        if footer:
            message_parts.append(footer)
        
        # Assembler le message
        full_message = "\n\n".join(message_parts)
        
        # Vérifier la longueur
        if len(full_message) > self.settings.max_message_length:
            full_message = full_message[:self.settings.max_message_length - 50] + "\n\n[Message tronqué]"
        
        return full_message
    
    def _is_quiet_hour(self, hour: int) -> bool:
        """Vérifie si on est dans les heures silencieuses"""
        if not self.settings.respect_quiet_hours:
            return False
        
        start = self.settings.quiet_start
        end = self.settings.quiet_end
        
        if start < end:
            return start <= hour < end
        else:  # Période à cheval sur minuit
            return hour >= start or hour < end
    
    def _should_send(
        self,
        config: ScheduledNotificationConfig,
        market: MarketData,
        opportunity: Optional[OpportunityScore],
    ) -> bool:
        """Vérifie si la notification doit être envoyée selon les seuils"""
        
        # Seuil de variation
        if config.send_only_if_change_above is not None:
            if not market.price_change_24h:
                return False
            if abs(market.price_change_24h) < config.send_only_if_change_above:
                return False
        
        # Seuil d'opportunité
        if config.send_only_if_opportunity_above is not None:
            if not opportunity:
                return False
            if opportunity.score < config.send_only_if_opportunity_above:
                return False
        
        return True
    
    def _generate_header(self, symbol: str, config: ScheduledNotificationConfig, hour: int) -> str:
        """Génère l'en-tête de la notification"""
        
        # Déterminer le moment de la journée
        if 5 <= hour < 12:
            time_slot = "matin"
            emoji = "🌅"
        elif 12 <= hour < 18:
            time_slot = "après-midi"
            emoji = "☀️"
        elif 18 <= hour < 23:
            time_slot = "soir"
            emoji = "🌆"
        else:
            time_slot = "nuit"
            emoji = "🌙"
        
        # Template personnalisable
        header_template = config.header_message or self.settings.global_header_template
        header = header_template.format(
            symbol=symbol,
            time_slot=time_slot,
            emoji=emoji,
            hour=hour
        )
        
        return header
    
    def _generate_footer(self, config: ScheduledNotificationConfig) -> str:
        """Génère le pied de page"""
        footer_template = config.footer_message or self.settings.global_footer_template
        return footer_template
    
    def _generate_block(
        self,
        block_name: str,
        config: ScheduledNotificationConfig,
        symbol: str,
        market: MarketData,
        prediction: Optional[Prediction],
        opportunity: Optional[OpportunityScore],
        all_markets: Dict[str, MarketData],
        all_predictions: Dict[str, Prediction],
        all_opportunities: Dict[str, OpportunityScore],
    ) -> Optional[str]:
        """Génère le contenu d'un bloc spécifique"""
        
        if block_name == "header" or block_name == "footer":
            return None  # Gérés séparément
        
        # Récupérer la configuration du bloc
        block = config.get_block(block_name)
        if not block or not block.enabled:
            return None
        
        # Générer selon le type
        if block_name == "price":
            return self._generate_price_block(market, config.price_block, config.kid_friendly_mode)
        
        elif block_name == "chart":
            return self._generate_chart_block(market, config.chart_block)
        
        elif block_name == "prediction":
            return self._generate_prediction_block(prediction, config.prediction_block, config.kid_friendly_mode)
        
        elif block_name == "opportunity":
            return self._generate_opportunity_block(opportunity, config.opportunity_block, config.kid_friendly_mode)
        
        elif block_name == "brokers":
            return self._generate_brokers_block(symbol, market, config.brokers_block)
        
        elif block_name == "fear_greed":
            return self._generate_fear_greed_block(config.fear_greed_block, config.kid_friendly_mode)
        
        elif block_name == "gain_loss":
            return self._generate_gain_loss_block(market, config.gain_loss_block, config.kid_friendly_mode)
        
        elif block_name == "investment_suggestions":
            return self._generate_investment_suggestions_block(
                symbol, all_markets, all_predictions, all_opportunities,
                config.investment_suggestions_block, config.kid_friendly_mode
            )
        
        elif block_name == "glossary":
            return self._generate_glossary_block(config.glossary_block)
        
        elif block_name == "custom":
            return self._generate_custom_blocks(config.custom_blocks)
        
        return None
    
    def _generate_price_block(
        self,
        market: MarketData,
        block: PriceBlock,
        kid_friendly: bool
    ) -> str:
        """Génère le bloc prix"""
        
        lines = []
        
        # Titre
        title = block.title if block.show_emoji else block.title.replace("💰", "").strip()
        lines.append(title)
        
        # Prix actuel
        if block.show_price_eur and market.current_price:
            price = market.current_price.price_eur
            if kid_friendly:
                lines.append(f"Le prix est de {price:.2f}€ maintenant")
                self.detected_terms.add("prix")
            else:
                lines.append(f"Prix actuel : {price:.2f}€")
        
        # Variation 24h
        if block.show_variation_24h and market.price_change_24h is not None:
            change = market.price_change_24h
            emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            
            if kid_friendly:
                if change > 0:
                    lines.append(f"{emoji} Il a monté de +{change:.1f}% en 24h - C'est bien !")
                elif change < 0:
                    lines.append(f"{emoji} Il a baissé de {change:.1f}% en 24h - Le prix descend")
                else:
                    lines.append(f"{emoji} Le prix n'a pas changé en 24h - Il est stable")
                self.detected_terms.add("variation")
            else:
                lines.append(f"{emoji} Variation 24h : {change:+.1f}%")
        
        # Volume
        if block.show_volume and market.volume_24h:
            volume = market.volume_24h
            if kid_friendly:
                if volume > 1_000_000_000:
                    lines.append(f"🔊 Beaucoup de gens l'achètent aujourd'hui (volume très élevé)")
                elif volume > 100_000_000:
                    lines.append(f"🔊 Pas mal d'activité sur cette crypto")
                else:
                    lines.append(f"🔊 Activité normale sur cette crypto")
                self.detected_terms.add("volume")
            else:
                lines.append(f"🔊 Volume 24h : {volume:,.0f}€")
        
        # Commentaire pédagogique
        if block.add_price_comment and kid_friendly:
            if market.price_change_24h:
                if market.price_change_24h > 3:
                    lines.append(f"\n💬 {block.message_prix_monte}")
                elif market.price_change_24h < -3:
                    lines.append(f"\n💬 {block.message_prix_descend}")
                else:
                    lines.append(f"\n💬 {block.message_prix_stable}")
        
        return "\n".join(lines)
    
    def _generate_chart_block(self, market: MarketData, block: ChartBlock) -> str:
        """Génère le bloc graphique"""
        lines = []
        lines.append(block.title)
        
        if block.show_sparklines:
            # Générer des sparklines (mini-graphiques ASCII)
            for tf in block.timeframes:
                period_name = block.period_names.get(tf, f"{tf}h")
                lines.append(f"📊 {period_name} : [graphique sera généré]")
        
        if block.send_full_chart:
            lines.append("🖼️ Graphique complet envoyé dans le prochain message")
        
        return "\n".join(lines)
    
    def _generate_prediction_block(
        self,
        prediction: Optional[Prediction],
        block: PredictionBlock,
        kid_friendly: bool
    ) -> Optional[str]:
        """Génère le bloc prédiction"""
        
        if not prediction:
            return None
        
        # Vérifier confiance minimum
        if prediction.confidence < block.min_confidence_to_show:
            return None
        
        lines = []
        lines.append(block.title)
        
        # Type de prédiction
        if block.show_prediction_type:
            pred_type = prediction.prediction_type.value
            
            if kid_friendly:
                if pred_type == "HAUSSIER":
                    lines.append(f"{block.message_haussier}")
                    self.detected_terms.add("IA")
                elif pred_type == "BAISSIER":
                    lines.append(f"{block.message_baissier}")
                    self.detected_terms.add("IA")
                else:
                    lines.append(f"{block.message_neutre}")
                    self.detected_terms.add("IA")
            else:
                emoji = "🚀" if pred_type == "HAUSSIER" else "⬇️" if pred_type == "BAISSIER" else "🤷"
                lines.append(f"{emoji} Tendance : {pred_type}")
        
        # Confiance
        if block.show_confidence:
            confidence = prediction.confidence
            if kid_friendly:
                if confidence >= 75:
                    level = "très sûre"
                elif confidence >= 60:
                    level = "plutôt sûre"
                elif confidence >= 50:
                    level = "pas très sûre"
                else:
                    level = "peu sûre"
                lines.append(f"Confiance : {confidence:.0f}% - L'IA est {level}")
            else:
                lines.append(f"Confiance : {confidence:.0f}%")
        
        # Explication
        if block.show_explanation and kid_friendly:
            lines.append("\n💡 L'IA analyse plein de données pour deviner si le prix va monter ou descendre. Mais attention, elle peut se tromper !")
        
        return "\n".join(lines)
    
    def _generate_opportunity_block(
        self,
        opportunity: Optional[OpportunityScore],
        block: OpportunityBlock,
        kid_friendly: bool
    ) -> Optional[str]:
        """Génère le bloc opportunité"""
        
        if not opportunity:
            return None
        
        # Vérifier score minimum
        if opportunity.score < block.min_score_to_show:
            return None
        
        lines = []
        lines.append(block.title)
        
        # Score
        if block.show_score:
            score = opportunity.score
            stars = "⭐" * score + "☆" * (10 - score)
            
            if kid_friendly:
                lines.append(f"{stars} {score}/10")
                self.detected_terms.add("opportunité")
                
                if score >= 8:
                    lines.append(f"{block.message_excellent}")
                elif score >= 6:
                    lines.append(f"{block.message_bon}")
                elif score >= 4:
                    lines.append(f"{block.message_moyen}")
                else:
                    lines.append(f"{block.message_faible}")
            else:
                lines.append(f"Score : {score}/10 {stars}")
        
        # Recommandation
        if block.show_recommendation and opportunity.recommendation:
            lines.append(f"\n💡 {opportunity.recommendation}")
        
        # Raisons
        if block.show_reasons and opportunity.factors:
            if kid_friendly:
                lines.append("\nPourquoi ce score ?")
            else:
                lines.append("\nFacteurs :")
            
            for factor in opportunity.factors[:3]:  # Top 3
                lines.append(f"  • {factor}")
        
        return "\n".join(lines)
    
    def _generate_brokers_block(
        self,
        symbol: str,
        market: MarketData,
        block: BrokersBlock
    ) -> str:
        """Génère le bloc courtiers"""
        
        lines = []
        lines.append(block.title)
        
        self.detected_terms.add("courtier")
        
        # Placeholder - à implémenter avec les vraies données courtiers
        lines.append("🏆 Meilleur prix : Binance - 91,600€")
        lines.append("📋 Autres options :")
        lines.append("  • Revolut : 91,650€ (+0.05%)")
        lines.append("  • Kraken : 91,680€ (+0.09%)")
        
        if block.show_fees:
            lines.append("\n💰 N'oublie pas de compter les frais d'achat !")
        
        lines.append(f"\n{block.explanation}")
        
        return "\n".join(lines)
    
    def _generate_fear_greed_block(
        self,
        block: FearGreedBlock,
        kid_friendly: bool
    ) -> str:
        """Génère le bloc Fear & Greed"""
        
        lines = []
        lines.append(block.title)
        
        # Placeholder - à récupérer depuis une API
        fear_greed_index = 45  # Exemple
        
        if block.show_index:
            lines.append(f"📊 Indice : {fear_greed_index}/100")
        
        if block.show_interpretation:
            if fear_greed_index < 25:
                message = block.message_extreme_fear
            elif fear_greed_index < 45:
                message = block.message_fear
            elif fear_greed_index < 55:
                message = block.message_neutral
            elif fear_greed_index < 75:
                message = block.message_greed
            else:
                message = block.message_extreme_greed
            
            lines.append(f"\n{message}")
        
        return "\n".join(lines)
    
    def _generate_gain_loss_block(
        self,
        market: MarketData,
        block: GainLossBlock,
        kid_friendly: bool
    ) -> str:
        """Génère le bloc gain/perte"""
        
        lines = []
        lines.append(block.title)
        
        # Calculer gain/perte hypothétique
        if market.price_change_24h and market.current_price:
            amount = block.investment_amount
            gain_pct = market.price_change_24h
            gain_amount = amount * (gain_pct / 100)
            
            if gain_amount > 0:
                emoji = "✅"
                verb = "gagné"
            else:
                emoji = "❌"
                verb = "perdu"
            
            if kid_friendly:
                lines.append(f"\nSi tu avais mis {amount:.0f}€ il y a 24h :")
                lines.append(f"{emoji} Tu aurais {verb} {abs(gain_amount):.2f}€")
                lines.append(f"Ton argent vaudrait maintenant {amount + gain_amount:.2f}€")
            else:
                lines.append(f"{emoji} Investment de {amount:.0f}€ il y a 24h")
                lines.append(f"Gain/Perte : {gain_amount:+.2f}€ ({gain_pct:+.1f}%)")
        
        return "\n".join(lines)
    
    def _generate_investment_suggestions_block(
        self,
        current_symbol: str,
        all_markets: Dict[str, MarketData],
        all_predictions: Dict[str, Prediction],
        all_opportunities: Dict[str, OpportunityScore],
        block: InvestmentSuggestionBlock,
        kid_friendly: bool
    ) -> Optional[str]:
        """🆕 Génère le bloc suggestions d'investissement"""
        
        # Générer les suggestions
        suggestions = self.suggestion_service.generate_suggestions(
            current_symbol=current_symbol,
            all_market_data=all_markets,
            all_predictions=all_predictions,
            all_opportunities=all_opportunities,
            max_suggestions=block.max_suggestions,
            min_opportunity_score=block.min_opportunity_score,
            exclude_current=block.exclude_current,
            prefer_low_volatility=block.prefer_low_volatility,
            prefer_trending=block.prefer_trending,
            prefer_undervalued=block.prefer_undervalued,
        )
        
        if not suggestions:
            return None
        
        # Formater le message
        message = self.suggestion_service.format_suggestions_message(
            suggestions=suggestions,
            kid_friendly=kid_friendly,
            use_emojis=True
        )
        
        return message
    
    def _generate_glossary_block(self, block: GlossaryBlock) -> Optional[str]:
        """Génère le bloc glossaire"""
        
        if not self.detected_terms and not block.custom_terms:
            return None
        
        lines = []
        lines.append(block.title)
        lines.append("")
        
        # Termes détectés automatiquement
        if block.auto_detect_terms:
            for term in sorted(self.detected_terms):
                if term in block.default_glossary:
                    lines.append(f"• **{term.capitalize()}** : {block.default_glossary[term]}")
        
        # Termes personnalisés
        for term, definition in block.custom_terms.items():
            lines.append(f"• **{term}** : {definition}")
        
        if len(lines) <= 2:  # Seulement titre et ligne vide
            return None
        
        return "\n".join(lines)
    
    def _generate_custom_blocks(self, custom_blocks: List) -> Optional[str]:
        """Génère les blocs personnalisés"""
        if not custom_blocks:
            return None
        
        lines = []
        for block in custom_blocks:
            if block.enabled and block.content:
                lines.append(block.title)
                lines.append(block.content)
                lines.append("")
        
        return "\n".join(lines) if lines else None
