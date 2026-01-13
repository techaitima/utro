"""
Services package for the Utro Bot.
Contains business logic for posting, API integrations, scheduling, and user management.
"""

from .scheduler import start_scheduler, stop_scheduler
from .holidays_api import fetch_holidays_for_date
from .ai_content import generate_post_content
from .image_generator import generate_food_image
from .post_service import post_to_channel
from .user_service import (
    update_user_activity,
    load_user_data,
    save_user_data,
    ensure_data_file_exists
)

__all__ = [
    "start_scheduler",
    "stop_scheduler",
    "fetch_holidays_for_date",
    "generate_post_content",
    "generate_food_image",
    "post_to_channel",
    "update_user_activity",
    "load_user_data",
    "save_user_data",
    "ensure_data_file_exists"
]
