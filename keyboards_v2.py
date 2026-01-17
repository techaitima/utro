"""
Keyboards for the Utro Bot.
Contains both Reply and Inline keyboards.
Updated with new features: templates, settings, editing.
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
    """Cancel action keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove the reply keyboard."""
    return ReplyKeyboardRemove()


# ============================================
# SETTINGS KEYBOARDS
# ============================================

def settings_keyboard() -> InlineKeyboardMarkup:
    """
    Create main settings inline keyboard.
    """
    settings = get_settings()
    
    # Current values for display
    image_status = "✅" if settings.image_enabled else "❌"
    model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
    template_names = {
        TextTemplate.SHORT.value: "Короткий",
        TextTemplate.MEDIUM.value: "Средний",
        TextTemplate.LONG.value: "Длинный",
        TextTemplate.CUSTOM.value: "Свой"
    }
    template_name = template_names.get(settings.text_template, "Средний")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🖼 Изображение: {image_status}", 
                    callback_data="toggle_image"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🎨 Модель: {model_name}", 
                    callback_data="select_model"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📝 Шаблон: {template_name}", 
                    callback_data="select_template"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Ссылка на канал", 
                    callback_data="channel_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Расписание", 
                    callback_data="schedule"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧪 Тесты API", 
                    callback_data="tests_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Главное меню", 
                    callback_data="back_main"
                )
            ]
        ]
    )
    return keyboard


def model_select_keyboard() -> InlineKeyboardMarkup:
    """Image model selection keyboard."""
    settings = get_settings()
    current = settings.image_model
    
    dalle_check = "✅ " if current == ImageModel.DALLE3.value else ""
    flux_check = "✅ " if current == ImageModel.FLUX.value else ""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{dalle_check}DALL-E 3 (OpenAI)", 
                    callback_data="set_model:dalle3"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{flux_check}Flux (Together AI)", 
                    callback_data="set_model:flux"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data="back_settings"
                )
            ]
        ]
    )
    return keyboard


def template_select_keyboard() -> InlineKeyboardMarkup:
    """Text template selection keyboard."""
    settings = get_settings()
    current = settings.text_template
    
    def check(t): return "✅ " if current == t else ""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.SHORT.value)}📄 Короткий (до 800 символов)", 
                    callback_data="set_template:short"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.MEDIUM.value)}📃 Средний (до 1024 символов)", 
                    callback_data="set_template:medium"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.LONG.value)}📜 Длинный (несколько сообщений)", 
                    callback_data="set_template:long"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.CUSTOM.value)}✏️ Свой шаблон", 
                    callback_data="set_template:custom"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Сбросить свой шаблон", 
                    callback_data="reset_custom_template"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data="back_settings"
                )
            ]
        ]
    )
    return keyboard


def tests_menu_keyboard() -> InlineKeyboardMarkup:
    """API tests menu keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 Тест DALL-E 3", 
                    callback_data="test_dalle"
                ),
                InlineKeyboardButton(
                    text="🌟 Тест Flux", 
                    callback_data="test_flux"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤖 Тест GPT-4o mini", 
                    callback_data="test_gpt"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎉 Тест праздников", 
                    callback_data="test_holidays"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📈 Моя статистика", 
                    callback_data="my_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data="back_settings"
                )
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


# ============================================
# POST PREVIEW & EDITING KEYBOARDS
# ============================================

def preview_post_keyboard(post_id: str = "") -> InlineKeyboardMarkup:
    """
    Create keyboard for post preview with publish/edit/cancel/regenerate buttons.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать", 
                    callback_data=f"publish_post:{post_id}" if post_id else "publish_post"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать", 
                    callback_data=f"edit_post:{post_id}" if post_id else "edit_post"
                ),
                InlineKeyboardButton(
                    text="🔄 Регенерировать", 
                    callback_data=f"regenerate_post:{post_id}" if post_id else "regenerate_post"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить", 
                    callback_data=f"cancel_preview:{post_id}" if post_id else "cancel_preview"
                )
            ]
        ]
    )
    return keyboard


def editing_post_keyboard(post_id: str = "") -> InlineKeyboardMarkup:
    """
    Keyboard shown during post editing.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💾 Сохранить изменения", 
                    callback_data=f"save_edit:{post_id}" if post_id else "save_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить редактирование", 
                    callback_data=f"cancel_edit:{post_id}" if post_id else "cancel_edit"
                )
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


# ============================================
# IMAGE POST KEYBOARDS
# ============================================

def image_category_keyboard() -> InlineKeyboardMarkup:
    """Category selection for post from image."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🥗 ПП рецепт", 
                    callback_data="img_cat:pp"
                ),
                InlineKeyboardButton(
                    text="🥑 Кето рецепт", 
                    callback_data="img_cat:keto"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨‍🍳 Кулинарный", 
                    callback_data="img_cat:culinary"
                ),
                InlineKeyboardButton(
                    text="🌅 Завтрак", 
                    callback_data="img_cat:breakfast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🍰 Десерт", 
                    callback_data="img_cat:dessert"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", 
                    callback_data="cancel_image_post"
                )
            ]
        ]
    )
    return keyboard


def image_post_options_keyboard(post_id: str = "") -> InlineKeyboardMarkup:
    """Options for post generated from image."""
    settings = get_settings()
    gen_image = "✅" if settings.image_enabled else "❌"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🖼 Генерировать изображение: {gen_image}", 
                    callback_data=f"toggle_img_gen:{post_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать", 
                    callback_data=f"publish_img_post:{post_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать", 
                    callback_data=f"edit_img_post:{post_id}"
                ),
                InlineKeyboardButton(
                    text="🔄 Регенерировать", 
                    callback_data=f"regen_img_post:{post_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить", 
                    callback_data="cancel_image_post"
                )
            ]
        ]
    )
    return keyboard


# ============================================
# CHANNEL LINK SETTINGS
# ============================================

def channel_link_keyboard() -> InlineKeyboardMarkup:
    """Channel link settings keyboard."""
    settings = get_settings()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Изменить название", 
                    callback_data="edit_channel_name"
                )
            ],
            [
                InlineKeyboardButton(
                    text="😀 Изменить эмодзи", 
                    callback_data="edit_channel_emoji"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Изменить ссылку", 
                    callback_data="edit_channel_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Текущее: {settings.channel_emoji} {settings.channel_name}", 
                    callback_data="noop"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data="back_settings"
                )
            ]
        ]
    )
    return keyboard


# ============================================
# RECIPE TYPE KEYBOARD
# ============================================

def recipe_type_keyboard() -> InlineKeyboardMarkup:
    """Recipe type selection (PP/Keto/Mixed)."""
    settings = get_settings()
    current = settings.recipe_type
    
    def check(t): return "✅ " if current == t else ""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{check('pp')}🥗 ПП (Правильное питание)", 
                    callback_data="set_recipe_type:pp"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check('keto')}🥑 Кето (низкие углеводы)", 
                    callback_data="set_recipe_type:keto"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check('mixed')}🔄 Смешанный", 
                    callback_data="set_recipe_type:mixed"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад", 
                    callback_data="back_settings"
                )
            ]
        ]
    )
    return keyboard


# ============================================
# LEGACY KEYBOARDS (kept for compatibility)
# ============================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Create admin control keyboard (legacy)."""
    return settings_keyboard()


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
                    url=f"https://t.me/{channel_id.replace('@', '')}" if channel_id.startswith('@') else "#"
                )
            ]
        ]
    )
    return keyboard
