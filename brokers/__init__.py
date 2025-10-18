"""
Courtier package - découverte automatique des implémentations.
"""

from importlib import import_module
import pkgutil
from typing import List, Type

from .base import Broker


def discover_brokers() -> List[Broker]:
    """Importe dynamiquement tous les courtiers disponibles."""

    brokers: List[Broker] = []

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_") or module_info.name == "base":
            continue
        module = import_module(f"{__name__}.{module_info.name}")
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isinstance(attribute, type) and issubclass(attribute, Broker) and attribute is not Broker:
                brokers.append(attribute())
    return brokers


__all__ = ["Broker", "discover_brokers"]
