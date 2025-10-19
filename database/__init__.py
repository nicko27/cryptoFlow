"""
Database Package
"""

from pathlib import Path

__version__ = "1.0.0"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

__all__ = []
