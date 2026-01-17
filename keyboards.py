"""
Keyboards for the Utro Bot.
Contains both Reply and Inline keyboards.
Updated with template, model selection, and image-from-photo features.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

from services.settings_service import get_settings, TextTemplate, ImageModel


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
                KeyboardButton(text="📅 Сегодня"),
                KeyboardButton(text="📊 Статус")
            ],
            [
                KeyboardButton(text="🖼 Пост из фото"),
                KeyboardButton(text="⚙️ Настройки")
            ],
            [
                KeyboardButton(text="ℹ️ Помощь")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def editing_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for editing mode with cancel button."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена редактирования")]],
        resize_keyboard=True
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove the reply keyboard."""
    return ReplyKeyboardRemove()


# ============================================
# INLINE KEYBOARDS (Contextual Menus)
# ============================================

def settings_keyboard() -> InlineKeyboardMarkup:
    """
    Create settings inline keyboard.
    Shows current settings values and options to change them.
    """
    settings = get_settings()
    
    # Format current values for display
    img_status = "✅ Вкл" if settings.image_enabled else "❌ Выкл"
    model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
    template_names = {
        TextTemplate.SHORT.value: "Короткий",
        TextTemplate.MEDIUM.value: "Средний",
        TextTemplate.LONG.value: "Длинный",
        TextTemplate.CUSTOM.value: "Кастомный"
    }
    template_name = template_names.get(settings.text_template, "Средний")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🖼 Изображения: {img_status}", 
                    callback_data="settings:image_toggle"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🎨 Модель: {model_name}", 
                    callback_data="settings:model_select"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📝 Шаблон: {template_name}", 
                    callback_data="settings:template_select"
                )
            ],
            [
                InlineKeyboardButton(text="⏰ Расписание", callback_data="schedule")
            ],
            [
                InlineKeyboardButton(text="🎨 Тест DALL-E", callback_data="test_dalle"),
                InlineKeyboardButton(text="🎉 Тест праздников", callback_data="test_holidays")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")
            ]
        ]
    )
    return keyboard


def model_select_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting image generation model."""
    settings = get_settings()
    
    dalle_check = "✅ " if settings.image_model == ImageModel.DALLE3.value else ""
    flux_check = "✅ " if settings.image_model == ImageModel.FLUX.value else ""
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{dalle_check}DALL-E 3 (OpenAI)", 
                    callback_data="model:DALLE3"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{flux_check}Flux (Together AI)", 
                    callback_data="model:FLUX"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_settings")
            ]
        ]
    )


def template_select_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting text template."""
    settings = get_settings()
    
    def check(t): 
        return "✅ " if settings.text_template == t else ""
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.SHORT.value)}📄 Короткий (~800)", 
                    callback_data="template:SHORT"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.MEDIUM.value)}📃 Средний (~1024)", 
                    callback_data="template:MEDIUM"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.LONG.value)}📜 Длинный (~4096)", 
                    callback_data="template:LONG"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.CUSTOM.value)}✏️ Кастомный", 
                    callback_data="template:CUSTOM"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_settings")
            ]
        ]
    )


def image_category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting recipe category when creating post from image."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥗 ПП", callback_data="cat:pp"),
                InlineKeyboardButton(text="🥑 Кето", callback_data="cat:keto")
            ],
            [
                InlineKeyboardButton(text="👨‍🍳 Кулинария", callback_data="cat:culinary")
            ],
            [
                InlineKeyboardButton(text="🍳 Завтраки", callback_data="cat:breakfast"),
                InlineKeyboardButton(text="🍰 Десерты", callback_data="cat:dessert")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
            ]
        ]
    )


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
    Create keyboard for post preview with publish/edit/regenerate/cancel buttons.
    All text in Russian.
    
    Args:
        post_id: Optional post identifier for callback data
    """
    pid = post_id or "0"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать", 
                    callback_data=f"publish:{pid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать", 
                    callback_data=f"edit:{pid}"
                ),
                InlineKeyboardButton(
                    text="🔄 Заново", 
                    callback_data=f"regenerate:{pid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить", 
                    callback_data=f"cancel:{pid}"
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
