"""
Courtier package - découverte automatique des implémentations
FIXED: Problème 17 - Gestion d'erreurs robuste pour import_module
"""

from importlib import import_module
import pkgutil
from typing import List, Type
import logging

from .base import Broker

# Setup logger
logger = logging.getLogger(__name__)


def discover_brokers() -> List[Broker]:
    """
    FIXED: Problème 17 - Import dynamique avec gestion d'erreurs
    Importe dynamiquement tous les courtiers disponibles
    """
    brokers: List[Broker] = []
    errors: List[str] = []

    for module_info in pkgutil.iter_modules(__path__):
        # Ignorer les modules privés et le module base
        if module_info.name.startswith("_") or module_info.name == "base":
            continue
        
        try:
            # FIXED: Gestion d'erreurs pour chaque module
            module = import_module(f"{__name__}.{module_info.name}")
            
            # Chercher les classes Broker dans le module
            found_broker = False
            for attribute_name in dir(module):
                try:
                    attribute = getattr(module, attribute_name)
                    
                    # Vérifier que c'est une classe Broker (mais pas la classe de base)
                    if (isinstance(attribute, type) and 
                        issubclass(attribute, Broker) and 
                        attribute is not Broker):
                        
                        # Instancier le broker
                        broker_instance = attribute()
                        brokers.append(broker_instance)
                        found_broker = True
                        logger.info(f"✓ Broker chargé: {attribute_name} depuis {module_info.name}")
                
                except Exception as e:
                    error_msg = f"Erreur instanciation {attribute_name} dans {module_info.name}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            if not found_broker:
                logger.debug(f"Aucun broker trouvé dans module {module_info.name}")
        
        except ImportError as e:
            error_msg = f"Erreur import module {module_info.name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        except Exception as e:
            error_msg = f"Erreur inattendue avec module {module_info.name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Log résumé
    logger.info(f"📊 Découverte brokers terminée: {len(brokers)} broker(s) chargé(s)")
    
    if errors:
        logger.warning(f"⚠️ {len(errors)} erreur(s) lors de la découverte des brokers")
        for error in errors:
            logger.debug(f"  - {error}")
    
    return brokers


__all__ = ["Broker", "discover_brokers"]
