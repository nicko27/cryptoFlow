"""
Messages configurables pour notifications
FIXED: Problème 10 - Messages centralisés et traduisibles
"""

from typing import Dict


class NotificationMessages:
    """Messages standardisés en français"""
    
    # Messages de prix
    PRICE_MESSAGES = {
        'rising': {
            'normal': "Le prix est en hausse",
            'kid_friendly': "📈 Le prix monte ! C'est une bonne nouvelle si tu possèdes déjà cette crypto."
        },
        'falling': {
            'normal': "Le prix est en baisse",
            'kid_friendly': "📉 Le prix baisse. Ça peut être un bon moment pour acheter si tu crois en cette crypto."
        },
        'stable': {
            'normal': "Le prix est stable",
            'kid_friendly': "➡️ Le prix est stable. Le marché hésite."
        },
        'volatile': {
            'normal': "Le prix est très volatil",
            'kid_friendly': "🎢 Le prix bouge beaucoup ! C'est normal avec les cryptos."
        }
    }
    
    # Messages de prédiction
    PREDICTION_MESSAGES = {
        'bullish': {
            'normal': "Tendance haussière prévue",
            'kid_friendly': "🚀 L'IA pense que le prix va monter"
        },
        'bearish': {
            'normal': "Tendance baissière prévue",
            'kid_friendly': "⬇️ L'IA pense que le prix va baisser"
        },
        'neutral': {
            'normal': "Pas de tendance claire",
            'kid_friendly': "🤷 L'IA ne voit pas de tendance claire"
        }
    }
    
    # Messages d'opportunité
    OPPORTUNITY_MESSAGES = {
        'excellent': {
            'normal': "Excellente opportunité d'investissement",
            'kid_friendly': "🌟 Excellente opportunité ! À surveiller de près."
        },
        'good': {
            'normal': "Bonne opportunité",
            'kid_friendly': "👍 Bonne opportunité, à considérer."
        },
        'medium': {
            'normal': "Opportunité moyenne",
            'kid_friendly': "⚖️ Opportunité moyenne, reste prudent."
        },
        'low': {
            'normal': "Opportunité faible",
            'kid_friendly': "⚠️ Opportunité faible, attends peut-être."
        }
    }
    
    # Raisons d'investissement
    INVESTMENT_REASONS = {
        'strong_trend': {
            'normal': "Forte tendance positive",
            'kid_friendly': "elle est en pleine forme"
        },
        'undervalued': {
            'normal': "Sous-évalué par rapport à la moyenne",
            'kid_friendly': "le prix est intéressant"
        },
        'good_prediction': {
            'normal': "Prédiction AI très positive",
            'kid_friendly': "l'IA est confiante"
        },
        'high_volume': {
            'normal': "Volume d'échanges élevé",
            'kid_friendly': "beaucoup de gens l'achètent"
        },
        'momentum': {
            'normal': "Momentum fort",
            'kid_friendly': "le mouvement reste puissant"
        },
        'recovery': {
            'normal': "Phase de récupération",
            'kid_friendly': "elle rebondit et reprend de la force"
        },
        'low_volatility': {
            'normal': "Faible volatilité",
            'kid_friendly': "elle est stable et rassurante"
        }
    }
    
    # Messages de risque
    RISK_MESSAGES = {
        'low': {
            'normal': "Risque faible",
            'kid_friendly': "🛡️ Peu risqué pour commencer"
        },
        'medium': {
            'normal': "Risque modéré",
            'kid_friendly': "⚖️ Risque moyen, sois attentif"
        },
        'high': {
            'normal': "Risque élevé",
            'kid_friendly': "⚠️ Assez risqué, fais attention"
        }
    }
    
    # Messages de recommandation
    RECOMMENDATION_MESSAGES = {
        'BUY': {
            'normal': "Achat recommandé",
            'kid_friendly': "💚 C'est peut-être le moment d'acheter"
        },
        'SELL': {
            'normal': "Vente recommandée",
            'kid_friendly': "❤️ Ça pourrait être le moment de vendre"
        },
        'HOLD': {
            'normal': "Conserver la position",
            'kid_friendly': "🟡 Garde ce que tu as, attends de voir"
        }
    }
    
    # Messages Fear & Greed
    FEAR_GREED_MESSAGES = {
        'extreme_fear': {
            'normal': "Peur extrême sur le marché",
            'kid_friendly': "😱 Tout le monde a très peur ! C'est parfois un bon moment pour acheter."
        },
        'fear': {
            'normal': "Peur sur le marché",
            'kid_friendly': "😰 Les gens ont peur. Le marché est nerveux."
        },
        'neutral': {
            'normal': "Sentiment neutre",
            'kid_friendly': "😐 Les gens ne savent pas trop quoi penser."
        },
        'greed': {
            'normal': "Avidité sur le marché",
            'kid_friendly': "🤑 Tout le monde veut acheter ! Attention à ne pas suivre la foule."
        },
        'extreme_greed': {
            'normal': "Avidité extrême sur le marché",
            'kid_friendly': "🤑💰 Euphorie totale ! C'est souvent le moment d'être prudent."
        }
    }
    
    # Messages généraux
    GENERAL_MESSAGES = {
        'unavailable': "Information non disponible",
        'error': "Erreur lors de la récupération",
        'loading': "Chargement...",
        'no_data': "Pas de données",
        'coming_soon': "Bientôt disponible"
    }
    
    # Disclaimers
    DISCLAIMERS = {
        'default': "💡 N'investis jamais plus que ce que tu peux te permettre de perdre !",
        'kid_friendly': "💡 Rappel important : demande toujours l'avis d'un adulte avant d'investir !",
        'risk_warning': "⚠️ Les cryptomonnaies sont très volatiles. Investis de manière responsable.",
        'not_financial_advice': "ℹ️ Ceci n'est pas un conseil financier, juste des informations."
    }
    
    # Glossaire par défaut
    DEFAULT_GLOSSARY = {
        'RSI': "Indice de Force Relative - Montre si la crypto est trop achetée (>70) ou trop vendue (<30)",
        'MACD': "Indicateur de tendance qui montre la direction du marché",
        'Support': "Prix plancher où la crypto a du mal à descendre",
        'Résistance': "Prix plafond où la crypto a du mal à monter",
        'Volume': "Quantité de crypto échangée - Un volume élevé = beaucoup d'intérêt",
        'Volatilité': "Mesure de la variation du prix - Haute volatilité = prix qui bouge beaucoup",
        'Market Cap': "Valeur totale de toutes les pièces en circulation",
        'ATH': "All-Time High - Le prix le plus haut jamais atteint",
        'ATL': "All-Time Low - Le prix le plus bas jamais atteint",
        'HODL': "Stratégie qui consiste à garder ses cryptos longtemps",
        'Bull Market': "Marché haussier - Les prix montent",
        'Bear Market': "Marché baissier - Les prix descendent",
        'Whale': "Gros investisseur qui possède beaucoup de crypto",
        'Pump': "Hausse rapide du prix",
        'Dump': "Chute rapide du prix"
    }
    
    @classmethod
    def get_message(cls, category: str, key: str, mode: str = 'normal') -> str:
        """
        Récupère un message par catégorie et clé
        
        Args:
            category: Catégorie de message (PRICE_MESSAGES, etc.)
            key: Clé du message
            mode: 'normal' ou 'kid_friendly'
        
        Returns:
            Le message approprié ou un fallback
        """
        messages_dict = getattr(cls, category, {})
        message_entry = messages_dict.get(key, {})
        
        if isinstance(message_entry, dict):
            return message_entry.get(mode, message_entry.get('normal', 'N/A'))
        
        return str(message_entry)
    
    @classmethod
    def get_price_message(cls, change_24h: float, kid_friendly: bool = False) -> str:
        """Retourne le message approprié selon la variation de prix"""
        mode = 'kid_friendly' if kid_friendly else 'normal'
        
        if change_24h > 5:
            return cls.get_message('PRICE_MESSAGES', 'rising', mode)
        elif change_24h < -5:
            return cls.get_message('PRICE_MESSAGES', 'falling', mode)
        elif abs(change_24h) > 10:
            return cls.get_message('PRICE_MESSAGES', 'volatile', mode)
        else:
            return cls.get_message('PRICE_MESSAGES', 'stable', mode)
    
    @classmethod
    def get_fear_greed_message(cls, index: int, kid_friendly: bool = False) -> str:
        """Retourne le message approprié selon l'indice Fear & Greed"""
        mode = 'kid_friendly' if kid_friendly else 'normal'
        
        if index < 25:
            return cls.get_message('FEAR_GREED_MESSAGES', 'extreme_fear', mode)
        elif index < 45:
            return cls.get_message('FEAR_GREED_MESSAGES', 'fear', mode)
        elif index < 55:
            return cls.get_message('FEAR_GREED_MESSAGES', 'neutral', mode)
        elif index < 75:
            return cls.get_message('FEAR_GREED_MESSAGES', 'greed', mode)
        else:
            return cls.get_message('FEAR_GREED_MESSAGES', 'extreme_greed', mode)
