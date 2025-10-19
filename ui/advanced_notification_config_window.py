"""
Wrapper pour l'interface de configuration avancée des notifications.

Le module d'origine vit dans ``core.services.advanced_notification_config_window``.
On le réexporte ici afin de conserver l'import attendu par l'UI.
"""

from core.services.advanced_notification_config_window import (
    AdvancedNotificationConfigWindow,
)

__all__ = ["AdvancedNotificationConfigWindow"]
