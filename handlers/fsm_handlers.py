"""
FSM Handlers for Utro Bot v3.0
Handles all FSM state transitions for custom inputs.
"""

import logging
import re
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import config
from keyboards import (
    main_menu_keyboard,
    settings_keyboard,
    schedule_keyboard,
    template_select_keyboard,
    new_post_category_keyboard,
    recipe_category_keyboard,
    preview_post_keyboard,
    cancel_keyboard,
    back_keyboard
)
from handlers.states import (
    ScheduleStates,
    TemplateStates,
    NewPostStates,
    EditPostStates
)
from services.user_service import update_user_activity
from services.settings_service import get_settings, update_settings
from utils.logger import mask_user_id

logger = logging.getLogger(__name__)
router = Router(name="fsm")


def is_admin(user_id: int) -> bool:
    """Check if user is authorized admin."""
    return config.is_admin(user_id)


# ============================================
# SCHEDULE - CUSTOM TIME INPUT
# ============================================

@router.message(ScheduleStates.waiting_for_custom_time, F.text)
async def process_custom_time(message: Message, state: FSMContext) -> None:
    """Process custom time input from user."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Отменено. Возвращаюсь к настройкам расписания.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Validate time format
    time_pattern = r'^(\d{1,2}):(\d{2})$'
    match = re.match(time_pattern, text)
    
    if not match:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Введите время в формате ЧЧ:ММ\n"
            "Например: <code>09:30</code> или <code>7:45</code>\n\n"
            "Отправьте /cancel для отмены.",
            parse_mode="HTML"
        )
        return
    
    hours = int(match.group(1))
    minutes = int(match.group(2))
    
    # Validate range
    if hours < 0 or hours > 23:
        await message.answer(
            "❌ <b>Неверные часы</b>\n\n"
            "Часы должны быть от 0 до 23.\n"
            "Введите время ещё раз:",
            parse_mode="HTML"
        )
        return
    
    if minutes < 0 or minutes > 59:
        await message.answer(
            "❌ <b>Неверные минуты</b>\n\n"
            "Минуты должны быть от 0 до 59.\n"
            "Введите время ещё раз:",
            parse_mode="HTML"
        )
        return
    
    # Format time properly
    formatted_time = f"{hours:02d}:{minutes:02d}"
    
    # Save to user settings (note: actual scheduler change requires .env update)
    update_settings(custom_schedule_time=formatted_time)
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Время сохранено: {formatted_time}</b>\n\n"
        f"⚠️ Для применения нового времени автопостинга\n"
        f"обновите MORNING_POST_TIME в .env файле\n"
        f"и перезапустите бота.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )
    
    logger.info(f"{mask_user_id(user_id, config.debug_mode)} set custom time: {formatted_time}")


# ============================================
# TEMPLATES - CUSTOM LENGTH INPUT
# ============================================

@router.message(TemplateStates.waiting_for_custom_length, F.text)
async def process_custom_length(message: Message, state: FSMContext) -> None:
    """Process custom post length input from user."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Отменено. Возвращаюсь к настройкам.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Validate number
    try:
        length = int(text)
    except ValueError:
        await message.answer(
            "❌ <b>Введите число</b>\n\n"
            "Укажите количество символов числом.\n"
            "Допустимый диапазон: 100 — 5000\n\n"
            "Например: <code>1500</code>",
            parse_mode="HTML"
        )
        return
    
    # Validate range
    if length < 100:
        await message.answer(
            "❌ <b>Слишком мало</b>\n\n"
            "Минимум: 100 символов\n"
            "Введите число от 100 до 5000:",
            parse_mode="HTML"
        )
        return
    
    if length > 5000:
        await message.answer(
            "❌ <b>Слишком много</b>\n\n"
            "Максимум: 5000 символов\n"
            "Введите число от 100 до 5000:",
            parse_mode="HTML"
        )
        return
    
    # Save custom length
    update_settings(text_template="CUSTOM", custom_length=length)
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Длина поста: {length} символов</b>\n\n"
        f"Посты будут генерироваться с учётом этого лимита.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )
    
    logger.info(f"{mask_user_id(user_id, config.debug_mode)} set custom length: {length}")


# ============================================
# NEW POST - CONTENT INPUT (Photo/Text)
# ============================================

@router.message(NewPostStates.waiting_for_content, F.photo)
async def process_content_photo(message: Message, state: FSMContext) -> None:
    """Process photo input for new post."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    # Get the largest photo
    photo = message.photo[-1]
    caption = message.caption or ""
    
    # Save photo file_id and caption to state
    await state.update_data(
        photo_file_id=photo.file_id,
        user_idea=caption,
        has_photo=True
    )
    
    # Move to prompt choice
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    prompt_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Дать промпт", callback_data="newpost_prompt:custom")],
            [InlineKeyboardButton(text="🤖 Автоматически", callback_data="newpost_prompt:auto")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:back")]
        ]
    )
    
    await message.answer(
        "📷 <b>Фото получено!</b>\n\n"
        "Хотите добавить промпт для генерации текста\n"
        "или бот создаст пост автоматически?",
        parse_mode="HTML",
        reply_markup=prompt_keyboard
    )
    
    await state.set_state(NewPostStates.waiting_for_prompt)
    logger.info(f"{mask_user_id(user_id, config.debug_mode)} uploaded photo for new post")


@router.message(NewPostStates.waiting_for_content, F.text)
async def process_content_text(message: Message, state: FSMContext) -> None:
    """Process text input for new post."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Создание поста отменено.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Save user's idea
    await state.update_data(
        user_idea=text,
        has_photo=False
    )
    
    # Move to prompt choice
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    prompt_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Дать промпт", callback_data="newpost_prompt:custom")],
            [InlineKeyboardButton(text="🤖 Автоматически", callback_data="newpost_prompt:auto")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="newpost:back")]
        ]
    )
    
    await message.answer(
        f"📝 <b>Идея сохранена!</b>\n\n"
        f"<i>«{text[:100]}{'...' if len(text) > 100 else ''}»</i>\n\n"
        f"Хотите добавить дополнительный промпт\n"
        f"или бот создаст пост автоматически?",
        parse_mode="HTML",
        reply_markup=prompt_keyboard
    )
    
    await state.set_state(NewPostStates.waiting_for_prompt)
    logger.info(f"{mask_user_id(user_id, config.debug_mode)} provided idea for new post")


@router.message(NewPostStates.waiting_for_prompt, F.text)
async def process_custom_prompt(message: Message, state: FSMContext) -> None:
    """Process custom prompt input."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Создание поста отменено.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Save prompt and trigger generation
    await state.update_data(custom_prompt=text)
    
    await message.answer(
        "⏳ <b>Генерирую пост...</b>\n\n"
        "Это может занять 1-2 минуты.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )
    
    # Generate post with all collected data
    await generate_new_post(message, state)


# ============================================
# POST EDITING
# ============================================

@router.message(EditPostStates.waiting_for_new_text, F.text)
async def process_edit_text(message: Message, state: FSMContext) -> None:
    """Process edited post text."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена редактирования", "❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Редактирование отменено.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Get post_id from state
    data = await state.get_data()
    post_id = data.get("editing_post_id")
    
    if not post_id:
        await state.clear()
        await message.answer(
            "⚠️ Пост не найден. Попробуйте заново.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Update pending post
    from services.post_service import get_pending_post, _pending_posts
    
    post_data = get_pending_post(post_id)
    if not post_data:
        await state.clear()
        await message.answer(
            "⚠️ Пост не найден. Возможно, он был удалён.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Update the text
    post_data["post_text"] = text
    _pending_posts[post_id] = post_data
    
    await state.clear()
    
    # Show updated preview
    from services.post_service import send_preview_to_admin
    
    await send_preview_to_admin(
        bot=message.bot,
        admin_id=user_id,
        post_data=post_data,
        reply_markup=preview_post_keyboard(post_id)
    )
    
    await message.answer(
        "✅ Текст обновлён! Смотрите превью выше.",
        reply_markup=main_menu_keyboard()
    )
    
    logger.info(f"{mask_user_id(user_id, config.debug_mode)} edited post {post_id}")


@router.message(EditPostStates.selecting_part, F.text)
async def process_select_part(message: Message, state: FSMContext) -> None:
    """Process part selection for multi-post editing."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Check for cancel
    if text in ["❌ Отмена", "/cancel"]:
        await state.clear()
        await message.answer(
            "Редактирование отменено.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Validate part number
    try:
        part_num = int(text)
    except ValueError:
        await message.answer(
            "❌ Введите номер части (число).",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    total_parts = data.get("total_parts", 1)
    
    if part_num < 1 or part_num > total_parts:
        await message.answer(
            f"❌ Введите номер от 1 до {total_parts}.",
            parse_mode="HTML"
        )
        return
    
    # Save selected part and ask for new text
    await state.update_data(editing_part=part_num)
    await state.set_state(EditPostStates.waiting_for_new_text)
    
    # Get current part text
    post_id = data.get("editing_post_id")
    from services.post_service import get_pending_post
    post_data = get_pending_post(post_id)
    
    if post_data and "parts" in post_data:
        current_text = post_data["parts"][part_num - 1]
        await message.answer(
            f"📝 <b>Редактирование части {part_num}/{total_parts}</b>\n\n"
            f"Текущий текст:\n<i>{current_text[:200]}...</i>\n\n"
            f"Отправьте новый текст для этой части:",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"Отправьте новый текст для части {part_num}:",
            parse_mode="HTML"
        )


# ============================================
# HELPER FUNCTIONS
# ============================================

async def generate_new_post(message: Message, state: FSMContext) -> None:
    """Generate new post with collected data."""
    user_id = message.from_user.id
    data = await state.get_data()
    
    category = data.get("category", "pp")
    user_idea = data.get("user_idea", "")
    custom_prompt = data.get("custom_prompt", "")
    has_photo = data.get("has_photo", False)
    photo_file_id = data.get("photo_file_id")
    
    await state.clear()
    
    try:
        from services.post_service import post_to_channel
        
        # Build combined prompt from user input
        combined_idea = user_idea
        if custom_prompt:
            combined_idea = f"{user_idea}\n\nДополнительно: {custom_prompt}"
        
        # Generate post
        success, post_id = await post_to_channel(
            bot=message.bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=user_id,
            recipe_category=category,
            custom_idea=combined_idea if combined_idea else None
        )
        
        if success and post_id:
            logger.info(f"New post generated: {post_id}")
        else:
            await message.answer(
                "❌ Не удалось сгенерировать пост. Попробуйте позже.",
                reply_markup=main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error generating new post: {e}", exc_info=True)
        await message.answer(
            f"⚠️ Ошибка при генерации: {str(e)[:100]}",
            reply_markup=main_menu_keyboard()
        )


# ============================================
# CANCEL HANDLER (catches ❌ Отмена button)
# ============================================

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Handle cancel button in any state."""
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
        await message.answer(
            "Действие отменено.",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            "Нечего отменять.",
            reply_markup=main_menu_keyboard()
        )
