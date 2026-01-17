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


class NewPostStates(StatesGroup):
    """States for new post creation flow."""
    # Step 1: Category selection (handled by callbacks, no state needed)
    
    # Step 2: Photo/Text input
    waiting_for_content = State()
    
    # Step 3: Prompt choice
    waiting_for_prompt = State()
    
    # Step 4-5: Generation and preview (handled by callbacks)
    
    # Step 6: Editing
    waiting_for_edit = State()
    waiting_for_edit_part = State()  # For multi-part posts


class EditPostStates(StatesGroup):
    """States for post editing."""
    waiting_for_new_text = State()
    selecting_part = State()  # Which part to edit in multi-post
