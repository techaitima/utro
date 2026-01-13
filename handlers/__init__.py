"""
Handlers package for the Utro Bot.
Contains admin, common, and callback handlers.
"""

from .admin import router as admin_router
from .common import router as common_router
from .callbacks import router as callbacks_router

__all__ = ["admin_router", "common_router", "callbacks_router"]
