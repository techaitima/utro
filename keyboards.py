"""
Inline keyboards for the Utro Bot.
Minimal keyboards for admin interactions.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Create admin control keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Отправить пост", callback_data="admin_post_now"),
            InlineKeyboardButton(text="📊 Статус", callback_data="admin_status")
        ],
        [
            InlineKeyboardButton(text="🎉 Тест праздников", callback_data="admin_test_holidays")
        ]
    ])
    return keyboard


def get_confirm_post_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard for posting."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_post"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")
        ]
    ])
    return keyboard


def get_channel_link_keyboard(channel_id: str) -> InlineKeyboardMarkup:
    """Create keyboard with channel link."""
    # Convert channel ID to username format if possible
    # For public channels, you would use the username
    # For private channels, we can't create a direct link
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Перейти в канал", 
                url="https://t.me/your_channel"  # Replace with actual channel link
            )
        ]
    ])
    return keyboard
