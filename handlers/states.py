"""
FSM States for Utro Bot v3.0
Defines all conversation states for multi-step interactions.
"""

from aiogram.fsm.state import State, StatesGroup


class ScheduleStates(StatesGroup):
    """States for schedule configuration."""
    waiting_for_custom_time = State()


class TemplateStates(StatesGroup):
    """States for template configuration."""
    waiting_for_custom_length = State()
    waiting_for_custom_template = State()  # Custom template text input


class NewPostStates(StatesGroup):
    """States for new post creation flow."""
    # Step 1: Category selection (handled by callbacks, no state needed)
    
    # Step 2: Photo/Text input
    waiting_for_content = State()
    waiting_for_custom_idea = State()
    waiting_for_custom_photo = State()
    waiting_for_text_after_photo = State()
    
    # Step 3: Prompt choice
    waiting_for_prompt = State()
    
    # Step 4-5: Generation and preview (handled by callbacks)
    
    # Step 6: Editing
    waiting_for_edit = State()
    waiting_for_edit_part = State()  # For multi-part posts


class RecipeStates(StatesGroup):
    """States for recipe creation with confirmation step."""
    confirming = State()
    waiting_for_custom_idea = State()
    waiting_for_custom_photo = State()


class PollStates(StatesGroup):
    """States for poll creation."""
    waiting_for_topic = State()


class TipStates(StatesGroup):
    """States for cooking tip creation."""
    waiting_for_topic = State()


class LifehackStates(StatesGroup):
    """States for kitchen lifehack creation."""
    waiting_for_topic = State()


class EditPostStates(StatesGroup):
    """States for post editing."""
    waiting_for_new_text = State()
    selecting_part = State()  # Which part to edit in multi-post


# Blacklist of menu button texts to ignore as input in FSM handlers
MENU_BUTTON_TEXTS = {
    "☀️ Утро сегодня", "📊 Статус", "✨ Новый пост", "⚙️ Настройки", "❔ Помощь",
    "🍳 Рецепт", "💡 Своя идея", "📊 Опрос", "💡 Совет", "🔧 Лайфхак",
    "❌ Отмена", "🔙 Назад", "⏭ Пропустить", "❌ Отмена редактирования",
    "/start", "/help", "/settings", "/cancel", "/status"
}


def is_menu_button(text: str) -> bool:
    """Check if text is a menu button that should be ignored in FSM handlers."""
    return text.strip() in MENU_BUTTON_TEXTS if text else False
