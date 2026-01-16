"""
Keyboards for the Utro Bot.
Contains both Reply and Inline keyboards.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)


# ============================================
# REPLY KEYBOARDS (Persistent Menu)
# ============================================

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Create the main persistent menu keyboard.
    Always visible at the bottom of the chat.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📨 Пост сейчас"),
                KeyboardButton(text="📊 Статус")
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="ℹ️ Помощь")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove the reply keyboard."""
    return ReplyKeyboardRemove()


# ============================================
# INLINE KEYBOARDS (Contextual Menus)
# ============================================

def settings_keyboard() -> InlineKeyboardMarkup:
    """
    Create settings inline keyboard.
    Contains testing options and schedule settings.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏰ Расписание", callback_data="schedule")
            ],
            [
                InlineKeyboardButton(text="🎨 Тест DALL-E", callback_data="test_dalle"),
                InlineKeyboardButton(text="🎉 Тест праздников", callback_data="test_holidays")
            ],
            [
                InlineKeyboardButton(text="🤖 Тест GPT-4o mini", callback_data="test_gpt")
            ],
            [
                InlineKeyboardButton(text="📈 Моя статистика", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")
            ]
        ]
    )
    return keyboard


def back_keyboard() -> InlineKeyboardMarkup:
    """Create a simple back button keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_settings")
            ]
        ]
    )
    return keyboard


def confirm_post_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard for posting."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_post"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_post")
            ]
        ]
    )
    return keyboard


def preview_post_keyboard(post_id: str = "") -> InlineKeyboardMarkup:
    """
    Create keyboard for post preview with publish/cancel/regenerate buttons.
    All text in Russian.
    
    Args:
        post_id: Optional post identifier for callback data
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать в канал", 
                    callback_data=f"publish_post:{post_id}" if post_id else "publish_post"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Регенерировать", 
                    callback_data=f"regenerate_post:{post_id}" if post_id else "regenerate_post"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить", 
                    callback_data=f"cancel_preview:{post_id}" if post_id else "cancel_preview"
                )
            ]
        ]
    )
    return keyboard


def schedule_keyboard() -> InlineKeyboardMarkup:
    """Create schedule settings keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏰ 06:00", callback_data="set_time_06"),
                InlineKeyboardButton(text="⏰ 07:00", callback_data="set_time_07"),
                InlineKeyboardButton(text="⏰ 08:00", callback_data="set_time_08")
            ],
            [
                InlineKeyboardButton(text="⏰ 09:00", callback_data="set_time_09"),
                InlineKeyboardButton(text="⏰ 10:00", callback_data="set_time_10"),
                InlineKeyboardButton(text="⏰ 12:00", callback_data="set_time_12")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_settings")
            ]
        ]
    )
    return keyboard


def test_result_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for test results with back button."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Повторить", callback_data="repeat_test")
            ],
            [
                InlineKeyboardButton(text="🔙 К настройкам", callback_data="back_settings")
            ]
        ]
    )
    return keyboard


# ============================================
# LEGACY KEYBOARDS (kept for compatibility)
# ============================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Create admin control keyboard (legacy)."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Отправить пост", callback_data="admin_post_now"),
                InlineKeyboardButton(text="📊 Статус", callback_data="admin_status")
            ],
            [
                InlineKeyboardButton(text="🎉 Тест праздников", callback_data="admin_test_holidays")
            ]
        ]
    )
    return keyboard


def get_confirm_post_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard for posting (legacy)."""
    return confirm_post_keyboard()


def get_channel_link_keyboard(channel_id: str) -> InlineKeyboardMarkup:
    """Create keyboard with channel link."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Перейти в канал", 
                    url="https://t.me/your_channel"
                )
            ]
        ]
    )
    return keyboard
