"""
User service for managing user data and activity tracking.
Stores user information in bot_users.json file.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

# Path to user data file
USER_DATA_FILE = Path(__file__).parent.parent / "data" / "bot_users.json"

# Lock for thread-safe file operations
_file_lock = asyncio.Lock()


def ensure_data_file_exists() -> None:
    """Create bot_users.json if it doesn't exist."""
    USER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USER_DATA_FILE.exists():
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        logger.info(f"Created user data file: {USER_DATA_FILE}")


def load_all_users() -> Dict[str, Any]:
    """
    Load all user data from file.
    
    Returns:
        Dictionary with all user data
    """
    ensure_data_file_exists()
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading user data: {e}")
        return {}


def save_all_users(data: Dict[str, Any]) -> None:
    """
    Save all user data to file.
    
    Args:
        data: Dictionary with all user data
    """
    ensure_data_file_exists()
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving user data: {e}", exc_info=True)


def load_user_data(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Load data for a specific user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        User data dictionary or None if not found
    """
    all_users = load_all_users()
    return all_users.get(str(user_id))


def save_user_data(user_id: int, data: Dict[str, Any]) -> None:
    """
    Save data for a specific user.
    
    Args:
        user_id: Telegram user ID
        data: User data dictionary
    """
    all_users = load_all_users()
    all_users[str(user_id)] = data
    save_all_users(all_users)


def update_user_activity(
    user_id: int,
    first_name: str = None,
    username: str = None,
    action: str = None
) -> Dict[str, Any]:
    """
    Update user's last activity and increment command counter.
    Creates new user record if doesn't exist.
    
    Args:
        user_id: Telegram user ID
        first_name: User's first name
        username: User's username
        action: Action performed (for logging)
    
    Returns:
        Updated user data
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    user_data = load_user_data(user_id)
    
    if user_data is None:
        # Create new user record
        user_data = {
            "first_name": first_name or "Unknown",
            "username": username or "",
            "first_seen": now,
            "last_active": now,
            "total_commands": 1,
            "posts_triggered": 0,
            "actions_log": []
        }
        logger.info(f"New user registered: {user_id} ({first_name})")
    else:
        # Update existing user
        user_data["last_active"] = now
        user_data["total_commands"] = user_data.get("total_commands", 0) + 1
        if first_name:
            user_data["first_name"] = first_name
        if username:
            user_data["username"] = username
    
    # Log action if provided
    if action:
        actions_log = user_data.get("actions_log", [])
        actions_log.append({
            "action": action,
            "timestamp": now
        })
        # Keep only last 50 actions
        user_data["actions_log"] = actions_log[-50:]
    
    save_user_data(user_id, user_data)
    return user_data


def increment_posts_triggered(user_id: int) -> None:
    """
    Increment the posts_triggered counter for a user.
    
    Args:
        user_id: Telegram user ID
    """
    user_data = load_user_data(user_id)
    if user_data:
        user_data["posts_triggered"] = user_data.get("posts_triggered", 0) + 1
        save_user_data(user_id, user_data)


def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user statistics.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        User statistics or None
    """
    return load_user_data(user_id)


def get_all_users_count() -> int:
    """Get total number of registered users."""
    return len(load_all_users())


def format_user_stats(user_id: int) -> str:
    """
    Format user statistics as readable text.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Formatted statistics string
    """
    user_data = load_user_data(user_id)
    if not user_data:
        return "Нет данных о пользователе"
    
    return f"""
👤 <b>Ваша статистика:</b>

• Имя: {user_data.get('first_name', 'Неизвестно')}
• Username: @{user_data.get('username', 'не указан')}
• Первый визит: {user_data.get('first_seen', 'Неизвестно')}
• Последняя активность: {user_data.get('last_active', 'Неизвестно')}
• Всего команд: {user_data.get('total_commands', 0)}
• Постов отправлено: {user_data.get('posts_triggered', 0)}
"""
