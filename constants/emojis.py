"""
Emojis centralisés pour les notifications
FIXED: Tous les emojis en un seul endroit pour cohérence
"""


class NotificationEmojis:
    """Emojis standardisés pour toutes les notifications"""
    
    # Prix et variations
    PRICE = "💰"
    PRICE_UP = "📈"
    PRICE_DOWN = "📉"
    PRICE_STABLE = "➡️"
    VOLUME = "📊"
    MARKET_CAP = "💎"
    
    # Alertes et niveaux
    INFO = "ℹ️"
    WARNING = "⚠️"
    IMPORTANT = "🔔"
    CRITICAL = "🚨"
    SUCCESS = "✅"
    ERROR = "❌"
    
    # Prédictions et tendances
    PREDICTION = "🔮"
    BULLISH = "🚀"
    SLIGHTLY_BULLISH = "📈"
    NEUTRAL = "🤷"
    SLIGHTLY_BEARISH = "📉"
    BEARISH = "⬇️"
    AI = "🤖"
    
    # Opportunités et risques
    OPPORTUNITY = "⭐"
    EXCELLENT_OPPORTUNITY = "🌟"
    GOOD_OPPORTUNITY = "👍"
    MEDIUM_OPPORTUNITY = "⚖️"
    LOW_OPPORTUNITY = "⚠️"
    
    # Niveaux de risque
    HIGH_RISK = "⚠️"
    MEDIUM_RISK = "⚖️"
    LOW_RISK = "🛡️"
    
    # Recommandations
    BUY = "💚"
    SELL = "❤️"
    HOLD = "🟡"
    
    # Moments de la journée
    MORNING = "🌅"
    NOON = "☀️"
    AFTERNOON = "🌤️"
    EVENING = "🌆"
    NIGHT = "🌙"
    
    # Sentiment marché
    FEAR = "😱"
    GREED = "🤑"
    SENTIMENT = "😐"
    
    # Courtiers et services
    BROKER = "🏦"
    CHART = "📈"
    GRAPH = "📊"
    
    # Indicateurs techniques
    RSI = "📉"
    MACD = "📊"
    MA = "📈"
    SUPPORT = "🛡️"
    RESISTANCE = "🚧"
    
    # Gain/Perte
    GAIN = "💰"
    LOSS = "📉"
    PROFIT = "💵"
    
    # Suggestions
    SUGGESTION = "💡"
    TIP = "📌"
    IDEA = "🎯"
    
    # Divers
    BELL = "🔔"
    ROCKET = "🚀"
    FIRE = "🔥"
    THINKING = "🤔"
    CELEBRATION = "🎉"
    CLOCK = "⏰"
    CALENDAR = "📅"
    DOCUMENT = "📄"
    
    @classmethod
    def get_time_emoji(cls, hour: int) -> str:
        """Retourne l'emoji adapté à l'heure"""
        if 5 <= hour < 12:
            return cls.MORNING
        elif 12 <= hour < 14:
            return cls.NOON
        elif 14 <= hour < 18:
            return cls.AFTERNOON
        elif 18 <= hour < 23:
            return cls.EVENING
        else:
            return cls.NIGHT
    
    @classmethod
    def get_change_emoji(cls, change: float) -> str:
        """Retourne l'emoji adapté au changement de prix"""
        if change > 5:
            return cls.BULLISH
        elif change > 0:
            return cls.PRICE_UP
        elif change > -5:
            return cls.PRICE_DOWN
        else:
            return cls.BEARISH
    
    @classmethod
    def get_alert_emoji(cls, level: str) -> str:
        """Retourne l'emoji adapté au niveau d'alerte"""
        level_map = {
            "INFO": cls.INFO,
            "WARNING": cls.WARNING,
            "IMPORTANT": cls.IMPORTANT,
            "CRITICAL": cls.CRITICAL,
        }
        return level_map.get(level.upper(), cls.INFO)
    
    @classmethod
    def get_opportunity_emoji(cls, score: int) -> str:
        """Retourne l'emoji adapté au score d'opportunité"""
        if score >= 8:
            return cls.EXCELLENT_OPPORTUNITY
        elif score >= 6:
            return cls.GOOD_OPPORTUNITY
        elif score >= 4:
            return cls.MEDIUM_OPPORTUNITY
        else:
            return cls.LOW_OPPORTUNITY
    
    @classmethod
    def get_risk_emoji(cls, risk_level: str) -> str:
        """Retourne l'emoji adapté au niveau de risque"""
        risk_map = {
            "LOW": cls.LOW_RISK,
            "MEDIUM": cls.MEDIUM_RISK,
            "HIGH": cls.HIGH_RISK,
        }
        return risk_map.get(risk_level.upper(), cls.MEDIUM_RISK)
