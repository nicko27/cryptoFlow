"""
Emojis pour les notifications
"""

class NotificationEmojis:
    """Emojis centralisés pour les notifications"""
    
    # Moments de la journée
    MORNING = "🌅"
    AFTERNOON = "☀️"
    EVENING = "🌆"
    NIGHT = "🌙"
    
    # Notifications
    BELL = "🔔"
    INFO = "ℹ️"
    WARNING = "⚠️"
    IMPORTANT = "🚨"
    
    # Prix et marché
    PRICE = "💰"
    CHART = "📊"
    UP = "📈"
    DOWN = "📉"
    VOLUME = "📊"
    
    # Prédictions
    CRYSTAL_BALL = "🔮"
    TARGET = "🎯"
    BRAIN = "🧠"
    
    # Opportunités
    STAR = "⭐"
    FIRE = "🔥"
    ROCKET = "🚀"
    GEM = "💎"
    
    # Actions
    BUY = "🟢"
    SELL = "🔴"
    HOLD = "🟡"
    
    # Autres
    BOOK = "📖"
    LIGHT_BULB = "💡"
    TROPHY = "🏆"
    MONEY = "💸"
    

    # Prédictions détaillées
    BULLISH = "🚀"
    BEARISH = "📉"
    NEUTRAL = "➡️"
    
    # Courtiers et plateformes
    BROKER = "🏦"
    EXCHANGE = "💱"
    
    # Sentiments
    SENTIMENT = "😊"
    FEAR = "😰"
    GREED = "🤑"
    AI = "🤖"
    
    # Gains et pertes
    GAIN = "💰"
    LOSS = "📉"
    PROFIT = "💵"
    
    # Suggestions
    SUGGESTION = "💡"
    IDEA = "🧠"
    TIP = "👉"

    @staticmethod
    def get_change_emoji(change_percent: float) -> str:
        """Retourne l'emoji correspondant à la variation"""
        if change_percent > 5:
            return "🚀"
        elif change_percent > 2:
            return "📈"
        elif change_percent > 0:
            return "🟢"
        elif change_percent > -2:
            return "🔴"
        elif change_percent > -5:
            return "📉"
        else:
            return "💥"
    
    @staticmethod
    def get_opportunity_emoji(score: int) -> str:
        """Retourne l'emoji correspondant au score d'opportunité"""
        if score >= 9:
            return "🔥"
        elif score >= 7:
            return "⭐"
        elif score >= 5:
            return "🟢"
        elif score >= 3:
            return "🟡"
        else:
            return "🔴"
    
    @staticmethod
    def get_prediction_emoji(prediction_type: str) -> str:
        """Retourne l'emoji correspondant au type de prédiction"""
        prediction_upper = prediction_type.upper()
        if "HAUSS" in prediction_upper or "BULL" in prediction_upper:
            return "🚀"
        elif "BAISS" in prediction_upper or "BEAR" in prediction_upper:
            return "📉"
        else:
            return "➡️"
