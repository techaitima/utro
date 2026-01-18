"""
Keyboards for the Utro Bot v3.0
Contains both Reply and Inline keyboards.
Updated with new post flow, neural network tests submenu, improved navigation.
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
                KeyboardButton(text="☀️ Утро сегодня"),
                KeyboardButton(text="📊 Статус")
            ],
            [
                KeyboardButton(text="✨ Новый пост"),
                KeyboardButton(text="⚙️ Настройки")
            ],
            [
                KeyboardButton(text="❔ Помощь")
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


def skip_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with skip and cancel buttons."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
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
    img_status = "вкл" if settings.image_enabled else "выкл"
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
                    text=f"🖼 Изображение: {img_status}", 
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
                InlineKeyboardButton(text="🧪 Тест нейросетей", callback_data="settings:neural_tests")
            ],
            [
                InlineKeyboardButton(text="📈 Моя статистика", callback_data="my_stats")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
            ]
        ]
    )
    return keyboard


def neural_tests_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for neural network tests submenu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🖼 Тест картинки", callback_data="test_image_confirm")
            ],
            [
                InlineKeyboardButton(text="🎉 Тест праздников", callback_data="test_holidays")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_settings")
            ]
        ]
    )


def confirm_image_test_keyboard() -> InlineKeyboardMarkup:
    """Confirmation dialog before generating test image."""
    settings = get_settings()
    model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Да, сгенерировать ({model_name})", 
                    callback_data="test_image_run"
                )
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="settings:neural_tests")
            ]
        ]
    )


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
                    text=f"{check(TextTemplate.SHORT.value)}📄 Короткий (~500 символов)", 
                    callback_data="template:SHORT"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.MEDIUM.value)}📃 Средний (~900 символов)", 
                    callback_data="template:MEDIUM"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.LONG.value)}📜 Длинный (~1800 символов)", 
                    callback_data="template:LONG"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{check(TextTemplate.CUSTOM.value)}✏️ Свой шаблон", 
                    callback_data="template:CUSTOM"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Задать кол-во символов", 
                    callback_data="template:custom_length"
                )
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_settings")
            ]
        ]
    )


def new_post_category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting new post category."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🍳 Рецепт", callback_data="newpost:recipe")
            ],
            [
                InlineKeyboardButton(text="💡 Своя идея", callback_data="newpost:custom")
            ],
            [
                InlineKeyboardButton(text="📊 Опрос", callback_data="newpost:poll"),
                InlineKeyboardButton(text="💡 Совет", callback_data="newpost:tip")
            ],
            [
                InlineKeyboardButton(text="🔧 Лайфхак", callback_data="newpost:lifehack")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
            ]
        ]
    )


def recipe_category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting recipe category."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥗 ПП", callback_data="recipe:pp"),
                InlineKeyboardButton(text="🥑 Кето", callback_data="recipe:keto")
            ],
            [
                InlineKeyboardButton(text="🌱 Веган", callback_data="recipe:vegan"),
                InlineKeyboardButton(text="🍵 Детокс", callback_data="recipe:detox")
            ],
            [
                InlineKeyboardButton(text="🍳 Завтраки", callback_data="recipe:breakfast"),
                InlineKeyboardButton(text="🍰 Десерты", callback_data="recipe:dessert")
            ],
            [
                InlineKeyboardButton(text="🥤 Смузи", callback_data="recipe:smoothie"),
                InlineKeyboardButton(text="🥣 Супы", callback_data="recipe:soup")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:back")
            ]
        ]
    )


def recipe_confirm_keyboard(category: str) -> InlineKeyboardMarkup:
    """Keyboard for recipe confirmation with options to add custom idea/photo."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✨ Сгенерировать", callback_data=f"recipe_gen:{category}")
            ],
            [
                InlineKeyboardButton(text="✏️ Добавить свою идею", callback_data=f"recipe_idea:{category}")
            ],
            [
                InlineKeyboardButton(text="📷 Добавить своё фото", callback_data=f"recipe_photo:{category}")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:recipe")
            ]
        ]
    )
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
                InlineKeyboardButton(text="⏰ 07:00", callback_data="set_time:07:00"),
                InlineKeyboardButton(text="⏰ 08:00", callback_data="set_time:08:00")
            ],
            [
                InlineKeyboardButton(text="⏰ 09:00", callback_data="set_time:09:00"),
                InlineKeyboardButton(text="⏰ 10:00", callback_data="set_time:10:00")
            ],
            [
                InlineKeyboardButton(text="🕐 Своё время", callback_data="set_time:custom")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_settings")
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
                InlineKeyboardButton(text="◀️ К настройкам", callback_data="back_settings")
            ]
        ]
    )
    return keyboard


def multipost_keyboard(post_id: str, part_num: int, total_parts: int) -> InlineKeyboardMarkup:
    """
    Keyboard for multi-part posts.
    Shows publish button only on last part.
    """
    buttons = []
    
    if part_num < total_parts:
        # Not the last part - show next button
        buttons.append([
            InlineKeyboardButton(
                text=f"➡️ Часть {part_num + 1}/{total_parts}",
                callback_data=f"multipost_next:{post_id}:{part_num + 1}"
            )
        ])
    else:
        # Last part - show publish button
        buttons.append([
            InlineKeyboardButton(
                text="✅ Опубликовать все части",
                callback_data=f"multipost_publish:{post_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"edit:{post_id}"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel:{post_id}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def photo_prompt_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for asking about photo attachment."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Создать без фото", callback_data="newpost:no_photo")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:back")
            ]
        ]
    )


def post_prompt_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for asking about post content."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Создать автоматически", callback_data="newpost:auto")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:back")
            ]
        ]
    )


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
