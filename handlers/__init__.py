"""
Handlers package for the Utro Bot.
Contains admin and common command handlers.
"""

from .admin import router as admin_router
from .common import router as common_router

__all__ = ["admin_router", "common_router"]
