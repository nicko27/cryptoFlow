"""
Utilitaires de formatage sécurisé pour notifications Telegram
FIXED: Gestion HTML propre, échappement, troncature intelligente
"""

import html
import re
from typing import Optional, Any
from datetime import datetime


class SafeHTMLFormatter:
    """Formatage HTML sécurisé pour Telegram"""
    
    @staticmethod
    def escape(text: str) -> str:
        """Échappe les caractères HTML spéciaux"""
        if not text:
            return ""
        return html.escape(str(text))
    
    @staticmethod
    def bold(text: str, escape: bool = True) -> str:
        """Texte en gras HTML"""
        content = SafeHTMLFormatter.escape(text) if escape else text
        return f"<b>{content}</b>"
    
    @staticmethod
    def italic(text: str, escape: bool = True) -> str:
        """Texte en italique HTML"""
        content = SafeHTMLFormatter.escape(text) if escape else text
        return f"<i>{content}</i>"
    
    @staticmethod
    def code(text: str, escape: bool = True) -> str:
        """Texte en code HTML"""
        content = SafeHTMLFormatter.escape(text) if escape else text
        return f"<code>{content}</code>"
    
    @staticmethod
    def link(url: str, text: str) -> str:
        """Lien HTML"""
        safe_url = SafeHTMLFormatter.escape(url)
        safe_text = SafeHTMLFormatter.escape(text)
        return f'<a href="{safe_url}">{safe_text}</a>'
    
    @staticmethod
    def truncate_safely(text: str, max_length: int = 4096) -> str:
        """
        Tronque le texte intelligemment sans casser HTML ou emojis
        FIXED: Problème 4 - Troncature sécurisée
        """
        if len(text) <= max_length:
            return text
        
        # Garder une marge pour le message de troncature
        safe_length = max_length - 50
        
        # Essayer de couper au dernier double saut de ligne (fin de paragraphe)
        last_paragraph = text.rfind('\n\n', 0, safe_length)
        if last_paragraph > safe_length // 2:  # Au moins à mi-chemin
            return text[:last_paragraph] + "\n\n" + SafeHTMLFormatter.italic("[Message tronqué pour respecter les limites Telegram]", escape=False)
        
        # Sinon, couper au dernier saut de ligne simple
        last_newline = text.rfind('\n', 0, safe_length)
        if last_newline > safe_length // 2:
            return text[:last_newline] + "\n" + SafeHTMLFormatter.italic("[Message tronqué]", escape=False)
        
        # En dernier recours, couper au dernier espace
        last_space = text.rfind(' ', 0, safe_length)
        if last_space > 0:
            return text[:last_space] + "... " + SafeHTMLFormatter.italic("[tronqué]", escape=False)
        
        # Cas extrême : couper brutalement
        return text[:safe_length] + "..."
    
    @staticmethod
    def validate_html(text: str) -> bool:
        """
        Valide que le HTML est bien formé (balises fermées)
        """
        # Compter les balises ouvertes/fermées
        open_tags = re.findall(r'<(b|i|code|a|pre)(?:\s|>)', text)
        close_tags = re.findall(r'</(b|i|code|a|pre)>', text)
        
        # Simple vérification : même nombre d'ouvertures et fermetures
        return len(open_tags) == len(close_tags)


class NumberFormatter:
    """Formatage cohérent des nombres"""
    
    @staticmethod
    def format_price(price: float, currency: str = "€", decimals: Optional[int] = None) -> str:
        """
        Formate un prix avec séparateurs de milliers
        FIXED: Problème 7 - Formatage cohérent
        """
        if price is None:
            return "N/A"
        
        # Déterminer automatiquement les décimales si non spécifié
        if decimals is None:
            if price >= 1:
                decimals = 2
            elif price >= 0.01:
                decimals = 4
            else:
                decimals = 8
        
        # Formater avec séparateurs d'espaces
        if price >= 1000:
            formatted = f"{price:,.{decimals}f}".replace(',', ' ')
        else:
            formatted = f"{price:.{decimals}f}"
        
        return f"{formatted} {currency}"

    @staticmethod
    def format_currency(value: float, currency: str = "€", decimals: Optional[int] = None) -> str:
        """
        Alias explicite pour le formatage de devises
        """
        return NumberFormatter.format_price(value, currency=currency, decimals=decimals)
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1, show_sign: bool = True) -> str:
        """
        Formate un pourcentage de manière cohérente
        """
        if value is None:
            return "N/A"
        
        sign = "+" if show_sign and value > 0 else ""
        return f"{sign}{value:.{decimals}f}%"
    
    @staticmethod
    def format_volume(volume: float, short: bool = False) -> str:
        """
        Formate un volume (avec notation K, M, B si demandé)
        """
        if volume is None:
            return "N/A"
        
        if short:
            if volume >= 1_000_000_000:
                return f"{volume / 1_000_000_000:.2f}B"
            elif volume >= 1_000_000:
                return f"{volume / 1_000_000:.2f}M"
            elif volume >= 1_000:
                return f"{volume / 1_000:.2f}K"
        
        return f"{volume:,.0f}".replace(',', ' ')
    
    @staticmethod
    def format_score(score: int, max_score: int = 10) -> str:
        """Formate un score sur une échelle"""
        if score is None:
            return "N/A"
        return f"{score}/{max_score}"


class SafeDataExtractor:
    """
    Extraction sécurisée de données depuis les objets
    FIXED: Problème 8 - Gestion d'erreurs
    """
    
    @staticmethod
    def get_price_eur(market: Optional[Any], default: str = "Prix indisponible") -> str:
        """Extrait le prix EUR de manière sécurisée"""
        try:
            if not market or not market.current_price:
                return default
            return NumberFormatter.format_price(market.current_price.price_eur)
        except Exception:
            return default
    
    @staticmethod
    def get_price_usd(market: Optional[Any], default: str = "Prix indisponible") -> str:
        """Extrait le prix USD de manière sécurisée"""
        try:
            if not market or not market.current_price:
                return default
            return NumberFormatter.format_price(market.current_price.price_usd, currency="$")
        except Exception:
            return default
    
    @staticmethod
    def get_change_24h(market: Optional[Any], default: str = "N/A") -> str:
        """Extrait la variation 24h de manière sécurisée"""
        try:
            if not market or not market.current_price:
                return default
            return NumberFormatter.format_percentage(market.current_price.change_24h)
        except Exception:
            return default
    
    @staticmethod
    def get_volume_24h(market: Optional[Any], default: str = "N/A") -> str:
        """Extrait le volume 24h de manière sécurisée"""
        try:
            if not market or not market.current_price:
                return default
            return NumberFormatter.format_volume(market.current_price.volume_24h, short=True)
        except Exception:
            return default

    @staticmethod
    def safe_price(price_obj: Optional[Any], default: float = 0.0) -> float:
        """Retourne un prix numérique sécurisé (en euros)"""
        try:
            if price_obj is None:
                return default
            if isinstance(price_obj, (int, float)):
                return float(price_obj)
            if hasattr(price_obj, "price_eur") and price_obj.price_eur is not None:
                return float(price_obj.price_eur)
            if hasattr(price_obj, "price") and price_obj.price is not None:
                return float(price_obj.price)
        except Exception:
            return default
        return default
    
    @staticmethod
    def get_prediction_type(prediction: Optional[Any], default: str = "Neutre") -> str:
        """Extrait le type de prédiction de manière sécurisée"""
        try:
            if not prediction:
                return default
            return prediction.prediction_type.value
        except Exception:
            return default
    
    @staticmethod
    def get_confidence(prediction: Optional[Any], default: int = 0) -> int:
        """Extrait la confiance de manière sécurisée"""
        try:
            if not prediction:
                return default
            return prediction.confidence
        except Exception:
            return default
    
    @staticmethod
    def get_opportunity_score(opportunity: Optional[Any], default: int = 0) -> int:
        """Extrait le score d'opportunité de manière sécurisée"""
        try:
            if not opportunity:
                return default
            return opportunity.score
        except Exception:
            return default
    
    @staticmethod
    def get_recommendation(opportunity: Optional[Any], default: str = "HOLD") -> str:
        """Extrait la recommandation de manière sécurisée"""
        try:
            if not opportunity:
                return default
            return opportunity.recommendation
        except Exception:
            return default


class TemplateFormatter:
    """
    Formatage sécurisé des templates
    FIXED: Problème 3 - Validation des templates
    """
    
    @staticmethod
    def format_template(template: str, **kwargs) -> str:
        """
        Formate un template avec gestion d'erreurs
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Variable manquante dans le template
            print(f"⚠️ Variable manquante dans template: {e}")
            # Créer un dict avec toutes les variables connues + placeholders pour manquantes
            all_vars = {}
            for match in re.finditer(r'\{(\w+)\}', template):
                var_name = match.group(1)
                if var_name in kwargs:
                    all_vars[var_name] = kwargs[var_name]
                else:
                    all_vars[var_name] = f"[{var_name}?]"
            
            return template.format(**all_vars)
        except Exception as e:
            print(f"❌ Erreur formatage template: {e}")
            return template
    
    @staticmethod
    def validate_template(template: str, allowed_variables: set) -> list:
        """
        Valide un template et retourne la liste des erreurs
        """
        errors = []
        
        # Extraire toutes les variables du template
        variables = set(re.findall(r'\{(\w+)\}', template))
        
        # Vérifier les variables inconnues
        unknown = variables - allowed_variables
        if unknown:
            errors.append(f"Variables inconnues: {', '.join(unknown)}")
        
        # Vérifier la syntaxe des accolades
        if template.count('{') != template.count('}'):
            errors.append("Accolades non équilibrées")
        
        return errors
