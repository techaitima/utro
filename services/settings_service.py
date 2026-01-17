"""
Bot Settings Service - persistent settings storage.
Stores user preferences: template, image model, channel link, etc.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)

# Settings file path
SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"


class TextTemplate(str, Enum):
    """Post text template options."""
    SHORT = "short"      # Always single post with image
    MEDIUM = "medium"    # Single post with image (may be truncated)
    LONG = "long"        # Can split into multiple posts
    CUSTOM = "custom"    # User-defined template


class ImageModel(str, Enum):
    """Image generation model options."""
    DALLE3 = "dalle3"    # OpenAI DALL-E 3
    FLUX = "flux"        # Flux model


class RecipeType(str, Enum):
    """Recipe type options."""
    PP = "pp"            # Правильное питание (default)
    KETO = "keto"        # Кетогенная диета
    MIXED = "mixed"      # Смешанный (иногда кето, иногда ПП)


@dataclass
class BotSettings:
    """Bot settings data class."""
    # Template settings
    text_template: str = TextTemplate.MEDIUM.value
    custom_template: str = ""
    
    # Image settings
    image_enabled: bool = True
    image_model: str = ImageModel.DALLE3.value
    
    # Channel link settings
    channel_name: str = "Utro | ПП рецепты"
    channel_emoji: str = "🍽"
    channel_link: str = ""  # Will be auto-generated from channel_id
    
    # Recipe settings
    recipe_type: str = RecipeType.PP.value
    
    # Flux API settings (if using Flux)
    flux_api_key: str = ""
    flux_api_url: str = "https://api.together.xyz/v1/images/generations"
    
    # Editing state
    editing_post_id: Optional[str] = None
    editing_message_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotSettings':
        """Create settings from dictionary."""
        # Filter only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


# Global settings instance
_settings: Optional[BotSettings] = None


def load_settings() -> BotSettings:
    """Load settings from file or create defaults."""
    global _settings
    
    if _settings is not None:
        return _settings
    
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _settings = BotSettings.from_dict(data)
                logger.info("Settings loaded from file")
        else:
            _settings = BotSettings()
            save_settings()
            logger.info("Created default settings")
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        _settings = BotSettings()
    
    return _settings


def save_settings() -> bool:
    """Save current settings to file."""
    global _settings
    
    if _settings is None:
        _settings = BotSettings()
    
    try:
        # Ensure data directory exists
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_settings.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info("Settings saved to file")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


def get_settings() -> BotSettings:
    """Get current settings (loads if not loaded)."""
    return load_settings()


def update_settings(**kwargs) -> BotSettings:
    """Update specific settings and save."""
    settings = get_settings()
    
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    save_settings()
    return settings


def set_template(template: TextTemplate, custom_text: str = "") -> BotSettings:
    """Set text template."""
    settings = get_settings()
    settings.text_template = template.value
    if template == TextTemplate.CUSTOM:
        settings.custom_template = custom_text
    save_settings()
    return settings


def set_image_model(model: ImageModel) -> BotSettings:
    """Set image generation model."""
    settings = get_settings()
    settings.image_model = model.value
    save_settings()
    return settings


def set_image_enabled(enabled: bool) -> BotSettings:
    """Enable or disable image generation."""
    settings = get_settings()
    settings.image_enabled = enabled
    save_settings()
    return settings


def set_channel_link(name: str, emoji: str, link: str = "") -> BotSettings:
    """Set channel link settings."""
    settings = get_settings()
    settings.channel_name = name
    settings.channel_emoji = emoji
    settings.channel_link = link
    save_settings()
    return settings


def set_editing_state(post_id: Optional[str], message_id: Optional[int]) -> BotSettings:
    """Set post editing state."""
    settings = get_settings()
    settings.editing_post_id = post_id
    settings.editing_message_id = message_id
    save_settings()
    return settings


def clear_editing_state() -> BotSettings:
    """Clear editing state."""
    return set_editing_state(None, None)


def get_channel_signature(channel_id: str = "") -> str:
    """
    Get formatted channel signature for posts.
    
    Returns:
        Formatted string like "🍽 @channel_name" or with link
    """
    settings = get_settings()
    
    if settings.channel_link:
        return f"\n\n{settings.channel_emoji} <a href=\"{settings.channel_link}\">{settings.channel_name}</a>"
    elif channel_id and channel_id.startswith("-100"):
        # Try to create link from channel ID (public channels only)
        return f"\n\n{settings.channel_emoji} {settings.channel_name}"
    else:
        return f"\n\n{settings.channel_emoji} {settings.channel_name}"


# Template length limits (in characters)
TEMPLATE_LIMITS = {
    TextTemplate.SHORT.value: 800,   # Short - always fits in caption
    TextTemplate.MEDIUM.value: 1024,  # Medium - Telegram caption limit
    TextTemplate.LONG.value: 4096,    # Long - can split into multiple messages
    TextTemplate.CUSTOM.value: 4096   # Custom - user defines
}


def get_template_limit() -> int:
    """Get character limit for current template."""
    settings = get_settings()
    return TEMPLATE_LIMITS.get(settings.text_template, 1024)


def should_split_post() -> bool:
    """Check if posts should be split (only for LONG template)."""
    settings = get_settings()
    return settings.text_template == TextTemplate.LONG.value
