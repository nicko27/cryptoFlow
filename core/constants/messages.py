"""
Messages pour les notifications
"""

class NotificationMessages:
    """Messages centralisés pour les notifications"""
    
    # Messages de prix
    PRICE_MESSAGES = {
        "strong_up": {
            "normal": "Forte hausse aujourd'hui !",
            "kid_friendly": "Super ! Le prix monte beaucoup aujourd'hui 🚀"
        },
        "up": {
            "normal": "Hausse modérée",
            "kid_friendly": "Le prix monte un peu 📈"
        },
        "stable": {
            "normal": "Prix stable",
            "kid_friendly": "Le prix ne bouge pas beaucoup 😌"
        },
        "down": {
            "normal": "Baisse modérée",
            "kid_friendly": "Le prix baisse un peu 📉"
        },
        "strong_down": {
            "normal": "Forte baisse aujourd'hui",
            "kid_friendly": "Attention ! Le prix baisse beaucoup 😰"
        }
    }
    
    # Messages d'opportunité
    OPPORTUNITY_MESSAGES = {
        "excellent": {
            "normal": "Excellente opportunité d'achat !",
            "kid_friendly": "C'est un très bon moment pour acheter ! ⭐"
        },
        "good": {
            "normal": "Bonne opportunité",
            "kid_friendly": "C'est un bon moment pour acheter 👍"
        },
        "neutral": {
            "normal": "Opportunité moyenne",
            "kid_friendly": "Tu peux acheter, mais ce n'est pas le meilleur moment 🤔"
        },
        "poor": {
            "normal": "Opportunité faible",
            "kid_friendly": "Ce n'est pas le meilleur moment pour acheter 😕"
        },
        "bad": {
            "normal": "Mauvaise opportunité",
            "kid_friendly": "Attends un peu avant d'acheter ! ⏸️"
        }
    }
    
    # Messages de prédiction
    PREDICTION_MESSAGES = {
        "bullish": {
            "normal": "Tendance haussière prévue",
            "kid_friendly": "Le robot pense que le prix va monter 🚀"
        },
        "bearish": {
            "normal": "Tendance baissière prévue",
            "kid_friendly": "Le robot pense que le prix va baisser 📉"
        },
        "neutral": {
            "normal": "Tendance neutre",
            "kid_friendly": "Le robot ne sait pas si ça va monter ou descendre 🤷"
        }
    }
    
    # Disclaimers
    DISCLAIMERS = {
        "default": "Ceci est une information, pas un conseil financier.",
        "kid_friendly": "N'investis jamais plus que ce que tu peux te permettre de perdre !",
        "detailed": "Les informations fournies ne constituent pas un conseil en investissement. Consultez un professionnel avant toute décision financière."
    }
    
    # Glossaire par défaut
    DEFAULT_GLOSSARY = {
        "RSI": "Indicateur qui montre si un actif est suracheté (>70) ou survendu (<30)",
        "Support": "Niveau de prix où l'achat est fort, empêchant la baisse",
        "Résistance": "Niveau de prix où la vente est forte, empêchant la hausse",
        "Volume": "Quantité d'actifs échangés sur une période",
        "Volatilité": "Amplitude des variations de prix",
        "Bull": "Marché en hausse, optimiste",
        "Bear": "Marché en baisse, pessimiste",
        "ATH": "All Time High - Plus haut historique",
        "ATL": "All Time Low - Plus bas historique",
        "HODL": "Stratégie consistant à garder ses actifs long terme"
    }
    
    @staticmethod
    def get_price_message(change_percent: float, kid_friendly: bool = False) -> str:
        """Retourne un message approprié selon la variation de prix"""
        key = "kid_friendly" if kid_friendly else "normal"
        
        if change_percent > 5:
            return NotificationMessages.PRICE_MESSAGES["strong_up"][key]
        elif change_percent > 2:
            return NotificationMessages.PRICE_MESSAGES["up"][key]
        elif change_percent > -2:
            return NotificationMessages.PRICE_MESSAGES["stable"][key]
        elif change_percent > -5:
            return NotificationMessages.PRICE_MESSAGES["down"][key]
        else:
            return NotificationMessages.PRICE_MESSAGES["strong_down"][key]
    
    @staticmethod
    def get_opportunity_message(score: int, kid_friendly: bool = False) -> str:
        """Retourne un message approprié selon le score d'opportunité"""
        key = "kid_friendly" if kid_friendly else "normal"
        
        if score >= 8:
            return NotificationMessages.OPPORTUNITY_MESSAGES["excellent"][key]
        elif score >= 6:
            return NotificationMessages.OPPORTUNITY_MESSAGES["good"][key]
        elif score >= 4:
            return NotificationMessages.OPPORTUNITY_MESSAGES["neutral"][key]
        elif score >= 2:
            return NotificationMessages.OPPORTUNITY_MESSAGES["poor"][key]
        else:
            return NotificationMessages.OPPORTUNITY_MESSAGES["bad"][key]
