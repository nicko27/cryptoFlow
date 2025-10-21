"""
Validateur de configuration de notifications
FIXED: Problème 9 - Validation des templates YAML
"""

import re
from typing import List, Dict, Any, Set
from pathlib import Path
import yaml


class NotificationConfigValidator:
    """Valide les fichiers de configuration de notifications"""
    
    # Variables autorisées dans les templates
    ALLOWED_TEMPLATE_VARS = {
        'symbol', 'time_slot', 'emoji', 'hour',
        'price', 'change_24h', 'volume', 'rsi',
        'prediction', 'confidence', 'score', 'recommendation'
    }
    
    # Blocs reconnus
    VALID_BLOCKS = {
        'header', 'price', 'chart', 'prediction', 'opportunity',
        'brokers', 'fear_greed', 'gain_loss', 
        'investment_suggestions', 'glossary', 'footer'
    }
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_file(self, config_path: str) -> bool:
        """
        Valide un fichier de configuration complet
        
        Returns:
            True si valide, False sinon
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Vérifier existence
        if not Path(config_path).exists():
            self.errors.append(f"Fichier non trouvé: {config_path}")
            return False
        
        # Charger YAML
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"Erreur parsing YAML: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Erreur lecture fichier: {e}")
            return False
        
        # Valider structure
        if not isinstance(config, dict):
            self.errors.append("La configuration doit être un dictionnaire")
            return False
        
        # Valider section globale
        if 'notifications' in config:
            self._validate_global_settings(config['notifications'])
        
        # Valider cryptos
        if 'coins' in config:
            self._validate_coins(config['coins'])
        
        return len(self.errors) == 0
    
    def _validate_global_settings(self, settings: Dict[str, Any]):
        """Valide les paramètres globaux"""
        
        # Vérifier types
        if 'enabled' in settings and not isinstance(settings['enabled'], bool):
            self.errors.append("notifications.enabled doit être un booléen")
        
        if 'kid_friendly_mode' in settings and not isinstance(settings['kid_friendly_mode'], bool):
            self.errors.append("notifications.kid_friendly_mode doit être un booléen")
        
        if 'max_message_length' in settings:
            length = settings['max_message_length']
            if not isinstance(length, int) or length < 100 or length > 4096:
                self.errors.append("notifications.max_message_length doit être entre 100 et 4096")
        
        # Valider heures par défaut
        if 'default_scheduled_hours' in settings:
            hours = settings['default_scheduled_hours']
            if not isinstance(hours, list):
                self.errors.append("default_scheduled_hours doit être une liste")
            else:
                for hour in hours:
                    if not isinstance(hour, int) or hour < 0 or hour > 23:
                        self.errors.append(f"Heure invalide dans default_scheduled_hours: {hour} (doit être 0-23)")
        
        # Valider quiet hours
        if 'quiet_hours' in settings:
            quiet = settings['quiet_hours']
            if not isinstance(quiet, dict):
                self.errors.append("quiet_hours doit être un dictionnaire")
            else:
                if 'start' in quiet:
                    start = quiet['start']
                    if not isinstance(start, int) or start < 0 or start > 23:
                        self.errors.append(f"quiet_hours.start invalide: {start} (doit être 0-23)")
                
                if 'end' in quiet:
                    end = quiet['end']
                    if not isinstance(end, int) or end < 0 or end > 23:
                        self.errors.append(f"quiet_hours.end invalide: {end} (doit être 0-23)")
        
        # Valider templates globaux
        if 'global_header_template' in settings:
            self._validate_template(
                settings['global_header_template'],
                "global_header_template"
            )
        
        if 'global_footer_template' in settings:
            self._validate_template(
                settings['global_footer_template'],
                "global_footer_template"
            )
    
    def _validate_coins(self, coins: Dict[str, Any]):
        """Valide la configuration des cryptos"""
        
        if not isinstance(coins, dict):
            self.errors.append("coins doit être un dictionnaire")
            return
        
        for symbol, coin_config in coins.items():
            # Valider symbole
            if not symbol.isupper():
                self.warnings.append(f"Symbole {symbol} devrait être en majuscules")
            
            if not isinstance(coin_config, dict):
                self.errors.append(f"Configuration de {symbol} doit être un dictionnaire")
                continue
            
            # Valider enabled
            if 'enabled' in coin_config and not isinstance(coin_config['enabled'], bool):
                self.errors.append(f"{symbol}.enabled doit être un booléen")
            
            # Valider notifications programmées
            if 'scheduled_notifications' in coin_config:
                notifications = coin_config['scheduled_notifications']
                if not isinstance(notifications, list):
                    self.errors.append(f"{symbol}.scheduled_notifications doit être une liste")
                else:
                    for i, notif in enumerate(notifications):
                        self._validate_scheduled_notification(symbol, i, notif)
    
    def _validate_scheduled_notification(self, symbol: str, index: int, notif: Dict[str, Any]):
        """Valide une notification programmée"""
        
        prefix = f"{symbol}.scheduled_notifications[{index}]"
        
        if not isinstance(notif, dict):
            self.errors.append(f"{prefix} doit être un dictionnaire")
            return
        
        # Valider nom
        if 'name' not in notif:
            self.warnings.append(f"{prefix} devrait avoir un 'name'")
        
        # Valider enabled
        if 'enabled' in notif and not isinstance(notif['enabled'], bool):
            self.errors.append(f"{prefix}.enabled doit être un booléen")
        
        # Valider hours
        if 'hours' in notif:
            hours = notif['hours']
            if not isinstance(hours, list):
                self.errors.append(f"{prefix}.hours doit être une liste")
            else:
                for hour in hours:
                    if not isinstance(hour, int) or hour < 0 or hour > 23:
                        self.errors.append(f"{prefix}.hours contient une heure invalide: {hour}")
        
        # Valider days_of_week
        if 'days_of_week' in notif:
            days = notif['days_of_week']
            if not isinstance(days, list):
                self.errors.append(f"{prefix}.days_of_week doit être une liste")
            else:
                for day in days:
                    if not isinstance(day, int) or day < 0 or day > 6:
                        self.errors.append(f"{prefix}.days_of_week contient un jour invalide: {day} (doit être 0-6)")
        
        # Valider blocks_order
        if 'blocks_order' in notif:
            blocks = notif['blocks_order']
            if not isinstance(blocks, list):
                self.errors.append(f"{prefix}.blocks_order doit être une liste")
            else:
                for block in blocks:
                    if block not in self.VALID_BLOCKS:
                        self.errors.append(f"{prefix}.blocks_order contient un bloc invalide: {block}")
        
        # Valider templates
        if 'header_message' in notif:
            self._validate_template(notif['header_message'], f"{prefix}.header_message")
        
        if 'footer_message' in notif:
            self._validate_template(notif['footer_message'], f"{prefix}.footer_message")
        
        # Valider seuils
        if 'send_only_if_change_above' in notif:
            threshold = notif['send_only_if_change_above']
            if not isinstance(threshold, (int, float)) or threshold < 0:
                self.errors.append(f"{prefix}.send_only_if_change_above doit être un nombre positif")
        
        if 'send_only_if_opportunity_above' in notif:
            threshold = notif['send_only_if_opportunity_above']
            if not isinstance(threshold, int) or threshold < 0 or threshold > 10:
                self.errors.append(f"{prefix}.send_only_if_opportunity_above doit être entre 0 et 10")
    
    def _validate_template(self, template: str, field_name: str):
        """Valide un template"""
        
        if not isinstance(template, str):
            self.errors.append(f"{field_name} doit être une chaîne")
            return
        
        # Extraire les variables
        variables = set(re.findall(r'\{(\w+)\}', template))
        
        # Vérifier variables inconnues
        unknown = variables - self.ALLOWED_TEMPLATE_VARS
        if unknown:
            self.warnings.append(
                f"{field_name} contient des variables inconnues: {', '.join(unknown)}"
            )
        
        # Vérifier accolades équilibrées
        if template.count('{') != template.count('}'):
            self.errors.append(f"{field_name} a des accolades non équilibrées")
        
        # Vérifier syntaxe format string
        try:
            # Test avec des valeurs dummy
            dummy_values = {var: 'test' for var in self.ALLOWED_TEMPLATE_VARS}
            template.format(**dummy_values)
        except KeyError as e:
            self.errors.append(f"{field_name} a une erreur de syntaxe: variable manquante {e}")
        except Exception as e:
            self.errors.append(f"{field_name} a une erreur de syntaxe: {e}")
    
    def get_report(self) -> str:
        """Retourne un rapport de validation"""
        lines = []
        
        if self.errors:
            lines.append("❌ ERREURS:")
            for error in self.errors:
                lines.append(f"  - {error}")
            lines.append("")
        
        if self.warnings:
            lines.append("⚠️ AVERTISSEMENTS:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
            lines.append("")
        
        if not self.errors and not self.warnings:
            lines.append("✅ Configuration valide !")
        
        return "\n".join(lines)
    
    def has_errors(self) -> bool:
        """Retourne True si des erreurs ont été détectées"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Retourne True si des avertissements ont été émis"""
        return len(self.warnings) > 0


def validate_notification_config(config_path: str) -> bool:
    """
    Fonction utilitaire pour valider un fichier de configuration
    
    Returns:
        True si valide, False sinon (affiche le rapport)
    """
    validator = NotificationConfigValidator()
    is_valid = validator.validate_file(config_path)
    
    print(validator.get_report())
    
    return is_valid


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python notification_config_validator.py <config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    is_valid = validate_notification_config(config_file)
    
    sys.exit(0 if is_valid else 1)
