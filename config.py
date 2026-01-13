"""
Configuration module for Utro Bot.
Loads environment variables and provides typed configuration.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""
    
    # Telegram Bot Token from @BotFather
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    
    # OpenAI API Key for GPT-4o mini and DALL-E 3
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # Calendarific API Key for holidays
    holidays_api_key: str = field(default_factory=lambda: os.getenv("HOLIDAYS_API_KEY", ""))
    
    # Telegram Channel ID (format: -100XXXXXXXXX)
    channel_id: str = field(default_factory=lambda: os.getenv("CHANNEL_ID", ""))
    
    # Admin User IDs (comma-separated)
    admin_user_ids: List[int] = field(default_factory=list)
    
    # Timezone for scheduling (default: Moscow)
    timezone: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Moscow"))
    
    # Morning post time in HH:MM format
    morning_post_time: str = field(default_factory=lambda: os.getenv("MORNING_POST_TIME", "08:00"))
    
    def __post_init__(self):
        """Parse complex configuration values after initialization."""
        # Parse admin user IDs from comma-separated string
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        if admin_ids_str:
            try:
                self.admin_user_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip()]
            except ValueError as e:
                logger.error(f"Error parsing ADMIN_USER_IDS: {e}")
                self.admin_user_ids = []
        
        # Validate required configuration
        self._validate()
    
    def _validate(self) -> None:
        """Validate that all required configuration is present."""
        errors = []
        
        if not self.bot_token:
            errors.append("BOT_TOKEN is required")
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.channel_id:
            errors.append("CHANNEL_ID is required")
        
        if not self.holidays_api_key:
            logger.warning("HOLIDAYS_API_KEY not set - will use fallback holiday generation")
        
        if not self.admin_user_ids:
            logger.warning("ADMIN_USER_IDS not set - admin commands will be disabled")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError(f"Missing required configuration: {', '.join(errors)}")
    
    def get_post_hour(self) -> int:
        """Get the hour component of morning post time."""
        try:
            return int(self.morning_post_time.split(":")[0])
        except (ValueError, IndexError):
            return 8
    
    def get_post_minute(self) -> int:
        """Get the minute component of morning post time."""
        try:
            return int(self.morning_post_time.split(":")[1])
        except (ValueError, IndexError):
            return 0
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user ID is in admin list."""
        return user_id in self.admin_user_ids


# Global configuration instance
config = Config()
