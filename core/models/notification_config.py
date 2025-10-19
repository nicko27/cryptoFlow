"""
Modèles de configuration avancés pour les notifications
Système ultra-paramétrable et compréhensible
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class NotificationTimeSlot(Enum):
    """Créneaux horaires de notification"""
    MATIN = "matin"  # 7h-11h
    MIDI = "midi"    # 11h-14h
    APRES_MIDI = "après-midi"  # 14h-18h
    SOIR = "soir"    # 18h-23h
    NUIT = "nuit"    # 23h-7h


@dataclass
class NotificationBlock:
    """Configuration d'un bloc d'information dans la notification"""
    enabled: bool = True
    title: str = ""  # Titre personnalisé du bloc (emoji + texte)
    show_emoji: bool = True
    custom_format: Optional[str] = None  # Format personnalisé
    explain_for_kids: bool = True  # Ajouter explications simples
    
    def __post_init__(self):
        """Validation après initialisation"""
        if not self.title:
            self.title = "Information"


@dataclass
class PriceBlock(NotificationBlock):
    """Bloc d'affichage du prix"""
    title: str = "💰 Prix actuel"
    show_price_eur: bool = True
    show_price_usd: bool = False
    show_variation_24h: bool = True
    show_variation_7d: bool = True
    show_volume: bool = True
    show_market_cap: bool = False
    add_price_comment: bool = True  # Commentaire pédagogique
    
    # Messages personnalisés selon situation
    message_prix_monte: str = "📈 Le prix monte ! C'est une bonne nouvelle si tu possèdes déjà cette crypto."
    message_prix_descend: str = "📉 Le prix baisse. Ça peut être un bon moment pour acheter si tu crois en cette crypto."
    message_prix_stable: str = "➡️ Le prix est stable. Le marché hésite."


@dataclass
class PredictionBlock(NotificationBlock):
    """Bloc de prédiction IA"""
    title: str = "🔮 Prédiction Intelligence Artificielle"
    show_prediction_type: bool = True  # Haussier/Baissier/Neutre
    show_confidence: bool = True
    show_explanation: bool = True
    min_confidence_to_show: int = 50  # Ne pas afficher si confiance < 50%
    
    # Messages personnalisés
    message_haussier: str = "🚀 L'IA pense que le prix va monter"
    message_baissier: str = "⬇️ L'IA pense que le prix va baisser"
    message_neutre: str = "🤷 L'IA ne voit pas de tendance claire"


@dataclass
class OpportunityBlock(NotificationBlock):
    """Bloc score d'opportunité"""
    title: str = "⭐ Score d'opportunité"
    show_score: bool = True
    show_recommendation: bool = True
    show_reasons: bool = True
    min_score_to_show: int = 0  # Afficher à partir de quel score
    
    # Messages personnalisés par niveau
    message_excellent: str = "🌟 Excellente opportunité ! À surveiller de près."
    message_bon: str = "👍 Bonne opportunité, à considérer."
    message_moyen: str = "⚖️ Opportunité moyenne, reste prudent."
    message_faible: str = "⚠️ Opportunité faible, attends peut-être."


@dataclass
class ChartBlock(NotificationBlock):
    """Bloc graphique"""
    title: str = "📊 Évolution du prix"
    show_sparklines: bool = True  # Mini-graphiques texte
    send_full_chart: bool = False  # Envoyer image graphique
    timeframes: List[int] = field(default_factory=lambda: [24, 168])  # heures
    show_support_resistance: bool = True
    
    # Noms conviviaux des périodes
    period_names: Dict[int, str] = field(default_factory=lambda: {
        1: "1 heure",
        4: "4 heures",
        24: "1 jour",
        168: "1 semaine",
        720: "1 mois"
    })


@dataclass
class BrokersBlock(NotificationBlock):
    """Bloc comparaison courtiers"""
    title: str = "💱 Où acheter le moins cher"
    show_best_price: bool = True
    show_all_brokers: bool = True
    show_fees: bool = True
    max_brokers_displayed: int = 3
    
    explanation: str = "Compare les prix sur différentes plateformes pour trouver la meilleure offre !"


@dataclass
class FearGreedBlock(NotificationBlock):
    """Bloc indice Fear & Greed"""
    title: str = "😨😁 Humeur du marché"
    show_index: bool = True
    show_interpretation: bool = True
    
    # Messages selon niveau
    message_extreme_fear: str = "😱 Peur extrême ! Les gens vendent beaucoup. Parfois c'est le moment d'acheter."
    message_fear: str = "😟 Le marché a peur. Les prix baissent souvent."
    message_neutral: str = "😐 Le marché est calme, ni peur ni avidité."
    message_greed: str = "😊 Le marché est optimiste. Les prix montent souvent."
    message_extreme_greed: str = "🤑 Avidité extrême ! Attention, les prix peuvent bientôt chuter."


@dataclass
class GainLossBlock(NotificationBlock):
    """Bloc gain/perte si investissement"""
    title: str = "💵 Si tu avais investi"
    show_gain_loss: bool = True
    show_percentage: bool = True
    investment_amount: float = 100.0  # Montant de référence
    
    message_gain: str = "✅ Tu aurais gagné {amount}€ (+{percent}%)"
    message_perte: str = "❌ Tu aurais perdu {amount}€ ({percent}%)"


@dataclass
class InvestmentSuggestionBlock(NotificationBlock):
    """🆕 Bloc suggestions d'investissement dans d'autres cryptos"""
    title: str = "💡 Autres cryptos intéressantes"
    enabled: bool = True
    max_suggestions: int = 3
    min_opportunity_score: int = 7  # Score minimum pour suggérer
    exclude_current: bool = True  # Ne pas suggérer la crypto actuelle
    
    # Critères de suggestion
    prefer_low_volatility: bool = False  # Préférer les cryptos stables
    prefer_trending: bool = True  # Préférer les cryptos en tendance
    prefer_undervalued: bool = True  # Préférer les cryptos sous-évaluées
    
    intro_message: str = "🔍 D'autres cryptos qui pourraient t'intéresser :"
    suggestion_template: str = "• {symbol} - Score {score}/10 - {reason}"
    
    # Messages selon type d'opportunité
    reason_strong_trend: str = "forte tendance haussière"
    reason_undervalued: str = "prix attractif"
    reason_high_volume: str = "beaucoup d'activité"
    reason_good_prediction: str = "prédiction IA positive"


@dataclass
class GlossaryBlock(NotificationBlock):
    """Bloc glossaire pédagogique"""
    title: str = "📚 Petit glossaire"
    enabled: bool = True
    auto_detect_terms: bool = True  # Détecter automatiquement les termes utilisés
    custom_terms: Dict[str, str] = field(default_factory=dict)  # Termes personnalisés
    
    # Glossaire par défaut
    default_glossary: Dict[str, str] = field(default_factory=lambda: {
        "crypto": "Monnaie numérique qui existe uniquement sur internet",
        "prix": "Combien coûte 1 unité de cette crypto en euros",
        "variation": "De combien le prix a changé (en % = sur 100)",
        "volume": "Combien d'argent total a été échangé",
        "tendance": "Direction générale du prix (monte, descend, ou stable)",
        "opportunité": "Chance d'acheter ou vendre au bon moment",
        "courtier": "Plateforme où on peut acheter des cryptos",
        "IA": "Intelligence Artificielle = ordinateur qui essaie de prédire le futur",
        "bull": "Marché qui monte (comme un taureau qui charge vers le haut)",
        "bear": "Marché qui descend (comme un ours qui frappe vers le bas)",
    })


@dataclass
class CustomMessageBlock(NotificationBlock):
    """Bloc message personnalisé libre"""
    title: str = "📝 Message spécial"
    content: str = ""
    position: str = "end"  # "start", "end", "after_price", etc.


@dataclass
class ScheduledNotificationConfig:
    """Configuration complète d'une notification programmée"""
    
    # Identification
    name: str = "Notification Standard"
    description: str = "Notification quotidienne"
    
    # Horaire
    hours: List[int] = field(default_factory=lambda: [9, 12, 18])
    time_slot: Optional[NotificationTimeSlot] = None
    
    # Activation
    enabled: bool = True
    days_of_week: List[int] = field(default_factory=lambda: [0,1,2,3,4,5,6])  # 0=Lundi
    
    # Contenu - ordre d'affichage
    blocks_order: List[str] = field(default_factory=lambda: [
        "header",
        "price",
        "chart",
        "prediction",
        "opportunity",
        "brokers",
        "fear_greed",
        "gain_loss",
        "investment_suggestions",  # 🆕 NOUVEAU
        "glossary",
        "custom",
        "footer"
    ])
    
    # Configuration de chaque bloc
    header_message: str = "🔔 {time_slot} - Mise à jour {symbol}"
    footer_message: str = "ℹ️ Ceci est une information, pas un conseil financier !"
    
    price_block: PriceBlock = field(default_factory=PriceBlock)
    prediction_block: PredictionBlock = field(default_factory=PredictionBlock)
    opportunity_block: OpportunityBlock = field(default_factory=OpportunityBlock)
    chart_block: ChartBlock = field(default_factory=ChartBlock)
    brokers_block: BrokersBlock = field(default_factory=BrokersBlock)
    fear_greed_block: FearGreedBlock = field(default_factory=FearGreedBlock)
    gain_loss_block: GainLossBlock = field(default_factory=GainLossBlock)
    investment_suggestions_block: InvestmentSuggestionBlock = field(default_factory=InvestmentSuggestionBlock)  # 🆕
    glossary_block: GlossaryBlock = field(default_factory=GlossaryBlock)
    custom_blocks: List[CustomMessageBlock] = field(default_factory=list)
    
    # Mode enfant renforcé
    kid_friendly_mode: bool = True
    use_emojis_everywhere: bool = True
    explain_everything: bool = True
    avoid_technical_terms: bool = True
    
    # Seuils d'envoi
    send_only_if_change_above: Optional[float] = None  # % de variation minimum
    send_only_if_opportunity_above: Optional[int] = None  # Score minimum
    
    def get_block(self, block_name: str) -> Optional[NotificationBlock]:
        """Récupère un bloc par son nom"""
        block_map = {
            "price": self.price_block,
            "prediction": self.prediction_block,
            "opportunity": self.opportunity_block,
            "chart": self.chart_block,
            "brokers": self.brokers_block,
            "fear_greed": self.fear_greed_block,
            "gain_loss": self.gain_loss_block,
            "investment_suggestions": self.investment_suggestions_block,
            "glossary": self.glossary_block,
        }
        return block_map.get(block_name)
    
    def is_active_now(self, hour: int, day_of_week: int) -> bool:
        """Vérifie si cette notification doit être envoyée maintenant"""
        if not self.enabled:
            return False
        if day_of_week not in self.days_of_week:
            return False
        if hour not in self.hours:
            return False
        return True


@dataclass
class CoinNotificationProfile:
    """Profil de notifications pour une crypto spécifique"""
    
    symbol: str
    enabled: bool = True
    
    # Notifications programmées pour cette crypto
    scheduled_notifications: List[ScheduledNotificationConfig] = field(default_factory=list)
    
    # Configuration par défaut si aucune notification planifiée ne correspond
    default_config: Optional[ScheduledNotificationConfig] = None
    
    # Surcharges spécifiques à cette crypto
    custom_emoji: Optional[str] = None  # Emoji personnalisé pour cette crypto
    nickname: Optional[str] = None  # Surnom convivial
    
    # Messages personnalisés
    intro_message: Optional[str] = None  # Message d'intro personnalisé
    outro_message: Optional[str] = None  # Message de fin personnalisé
    
    # Niveau de détail adaptatif
    detail_level: str = "normal"  # "simple", "normal", "detailed"
    
    def get_active_config(self, hour: int, day_of_week: int) -> Optional[ScheduledNotificationConfig]:
        """Récupère la configuration active pour l'heure donnée"""
        for config in self.scheduled_notifications:
            if config.is_active_now(hour, day_of_week):
                return config
        return self.default_config
    
    def add_scheduled_notification(self, config: ScheduledNotificationConfig):
        """Ajoute une notification programmée"""
        self.scheduled_notifications.append(config)


@dataclass
class GlobalNotificationSettings:
    """Paramètres globaux de notification"""
    
    # Activation générale
    enabled: bool = True
    
    # Mode enfant global
    kid_friendly_mode: bool = True
    max_message_length: int = 4096  # Limite Telegram
    
    # Gestion des horaires
    respect_quiet_hours: bool = True
    quiet_start: int = 23
    quiet_end: int = 7
    
    # Profils par crypto
    coin_profiles: Dict[str, CoinNotificationProfile] = field(default_factory=dict)
    
    # Configuration par défaut pour nouvelles cryptos
    default_scheduled_hours: List[int] = field(default_factory=lambda: [9, 12, 18])
    
    # Templates globaux
    global_header_template: str = "🔔 Notification Crypto {time_slot}"
    global_footer_template: str = "💡 N'investis jamais plus que ce que tu peux te permettre de perdre !"
    
    def get_coin_profile(self, symbol: str) -> CoinNotificationProfile:
        """Récupère ou crée le profil d'une crypto"""
        if symbol not in self.coin_profiles:
            self.coin_profiles[symbol] = self._create_default_profile(symbol)
        return self.coin_profiles[symbol]
    
    def _create_default_profile(self, symbol: str) -> CoinNotificationProfile:
        """Crée un profil par défaut pour une crypto"""
        profile = CoinNotificationProfile(
            symbol=symbol,
            enabled=True
        )
        
        # Créer configuration par défaut
        for hour in self.default_scheduled_hours:
            config = ScheduledNotificationConfig(
                name=f"Notification {hour}h",
                hours=[hour],
                enabled=True
            )
            profile.add_scheduled_notification(config)
        
        return profile
    
    def set_hours_for_all_coins(self, hours: List[int]):
        """Change les horaires pour toutes les cryptos"""
        self.default_scheduled_hours = hours
        for profile in self.coin_profiles.values():
            profile.scheduled_notifications.clear()
            for hour in hours:
                config = ScheduledNotificationConfig(
                    name=f"Notification {hour}h",
                    hours=[hour],
                    enabled=True
                )
                profile.add_scheduled_notification(config)
