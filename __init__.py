"""
CrAnki - Auto Rebuild Filtered Decks
Entry point for Anki addon - imports from src package
"""

from .src import cranki

# Re-export everything from the main module
__all__ = ["cranki"]
