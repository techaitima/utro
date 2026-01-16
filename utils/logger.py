"""
Logging utilities for Utro Bot.
Contains functions for masking sensitive data in logs.
"""

import re
from typing import Optional


def mask_sensitive(text: str, debug_mode: bool = False) -> str:
    """
    Masks sensitive data in logs for security.
    
    Rules:
    - API keys (sk-*): show first 4 + last 4 chars (sk-proj-ab***xyz)
    - Bot tokens: show first 4 + last 4 chars (1234***abcd)
    - User IDs (numbers > 6 digits): show last 3 digits (user_***789)
    - Channel IDs: show last 4 digits (channel_***4567)
    - Completely hide if too short to mask
    
    Args:
        text: Text that may contain sensitive data
        debug_mode: If True, return original text without masking
        
    Returns:
        Text with sensitive data masked (or original if debug_mode=True)
    """
    if debug_mode:
        return text
    
    if not text:
        return text
    
    result = str(text)
    
    # Mask OpenAI API keys (sk-proj-... or sk-...)
    result = re.sub(
        r'(sk-(?:proj-)?[a-zA-Z0-9]{2})[a-zA-Z0-9-]+([a-zA-Z0-9]{4})',
        r'\1***\2',
        result
    )
    
    # Mask Bot tokens (numbers:letters format)
    result = re.sub(
        r'(\d{4})\d+:([a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+([a-zA-Z0-9_-]{4})',
        r'\1***:\2***\3',
        result
    )
    
    # Mask Calendarific/Holiday API keys (typically alphanumeric)
    result = re.sub(
        r'(api_key=)([a-zA-Z0-9]{4})[a-zA-Z0-9]+([a-zA-Z0-9]{4})',
        r'\1\2***\3',
        result
    )
    
    return result


def mask_user_id(user_id: int, debug_mode: bool = False) -> str:
    """
    Mask a user ID for logging.
    
    Args:
        user_id: Telegram user ID
        debug_mode: If True, return full ID
        
    Returns:
        Masked user ID string (e.g., "user_***789")
    """
    if debug_mode:
        return str(user_id)
    
    user_str = str(user_id)
    if len(user_str) <= 3:
        return "user_***"
    
    return f"user_***{user_str[-3:]}"


def mask_channel_id(channel_id: str, debug_mode: bool = False) -> str:
    """
    Mask a channel ID for logging.
    
    Args:
        channel_id: Telegram channel ID (e.g., -100123456789)
        debug_mode: If True, return full ID
        
    Returns:
        Masked channel ID string (e.g., "channel_***6789")
    """
    if debug_mode:
        return str(channel_id)
    
    channel_str = str(channel_id).lstrip('-')
    if len(channel_str) <= 4:
        return "channel_***"
    
    return f"channel_***{channel_str[-4:]}"


def get_safe_log_message(
    message: str,
    user_id: Optional[int] = None,
    channel_id: Optional[str] = None,
    debug_mode: bool = False
) -> str:
    """
    Create a safe log message with all sensitive data masked.
    
    Args:
        message: Base log message
        user_id: Optional user ID to include
        channel_id: Optional channel ID to include
        debug_mode: If True, don't mask anything
        
    Returns:
        Safe log message with masked data
    """
    result = mask_sensitive(message, debug_mode)
    
    if user_id is not None:
        # Replace raw user ID with masked version
        result = result.replace(str(user_id), mask_user_id(user_id, debug_mode))
    
    if channel_id is not None:
        # Replace raw channel ID with masked version
        result = result.replace(str(channel_id), mask_channel_id(channel_id, debug_mode))
    
    return result
