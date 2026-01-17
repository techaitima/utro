"""
Bot handlers v2 - Updated handlers with all new features:
- Template selection
- Image model selection
- Post from image
- Editing with proper cancel
- Category selection
"""

import logging
import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from config import config
from keyboards_v2 import (
    main_menu_keyboard,
    settings_keyboard,
    preview_post_keyboard,
    confirm_publish_keyboard,
    image_category_keyboard,
    template_select_keyboard,
    model_select_keyboard,
    cancel_button,
    editing_keyboard,
    image_toggle_keyboard,
    back_to_settings_keyboard
)
from services.settings_service import (
    get_settings,
    update_settings,
    TextTemplate,
    ImageModel,
    RecipeType
)
from services.post_service_v2 import (
    post_to_channel,
    publish_pending_post,
    get_pending_post,
    update_pending_post,
    start_editing,
    get_editing_state,
    cancel_editing,
    finish_editing,
    generate_post_data,
    store_pending_post,
    send_preview_to_admin
)
from services.ai_content_v2 import analyze_image_for_post

logger = logging.getLogger(__name__)
router = Router()


# ============== FSM States ==============

class PostStates(StatesGroup):
    """States for post creation workflow."""
    waiting_for_image = State()
    selecting_category = State()
    editing_text = State()
    waiting_custom_template = State()


# ============== Helper Functions ==============

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id == config.admin_id


async def admin_only(message: Message) -> bool:
    """Filter for admin-only commands."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён. Этот бот только для администратора.")
        return False
    return True


async def admin_only_callback(callback: CallbackQuery) -> bool:
    """Filter for admin-only callbacks."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return False
    return True


# ============== Start & Help ==============

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    if not await admin_only(message):
        return
    
    await message.answer(
        "👋 <b>Привет! Я Utro Bot</b>\n\n"
        "Я создаю ежедневные посты с:\n"
        "• ☀️ Кулинарными праздниками\n"
        "• 🍳 ПП-рецептами (или Кето)\n"
        "• 📷 Красивыми изображениями\n\n"
        "Используй кнопки ниже для управления:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    if not await admin_only(message):
        return
    
    settings = get_settings()
    status_text = (
        f"📊 <b>Текущие настройки:</b>\n"
        f"• Изображения: {'✅ Вкл' if settings.image_enabled else '❌ Выкл'}\n"
        f"• Модель: {settings.image_model}\n"
        f"• Шаблон: {settings.text_template}\n"
        f"• Рецепты: {settings.recipe_type}\n"
    )
    
    await message.answer(
        "<b>📖 Справка по Utro Bot</b>\n\n"
        "<b>Главные команды:</b>\n"
        "/start - Начать работу\n"
        "/help - Эта справка\n"
        "/post - Создать пост на сегодня\n"
        "/settings - Открыть настройки\n"
        "/status - Статус автопостинга\n\n"
        f"{status_text}\n"
        "<b>Кнопки меню:</b>\n"
        "📅 <b>Сегодня</b> - Создать пост на сегодня\n"
        "🖼 <b>Пост из фото</b> - Создать пост по вашему фото\n"
        "⚙️ <b>Настройки</b> - Изменить шаблон, модель, расписание\n"
        "📊 <b>Статус</b> - Информация о боте",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


# ============== Main Menu Buttons ==============

@router.message(F.text == "📅 Сегодня")
async def btn_post_today(message: Message, bot: Bot):
    """Create post for today."""
    if not await admin_only(message):
        return
    
    status_msg = await message.answer("⏳ Генерирую пост на сегодня...")
    
    try:
        success, post_id = await post_to_channel(
            bot=bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=message.from_user.id
        )
        
        if success:
            await status_msg.delete()
        else:
            await status_msg.edit_text(
                "❌ Не удалось сгенерировать пост. Попробуйте ещё раз.",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Post generation error: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка: {e}")


@router.message(F.text == "📊 Статус")
async def btn_status(message: Message):
    """Show bot status."""
    if not await admin_only(message):
        return
    
    settings = get_settings()
    
    # Calculate next post time
    now = datetime.now()
    next_post = "Не запланирован"
    if settings.autopost_enabled and settings.morning_post_time:
        parts = settings.morning_post_time.split(":")
        if len(parts) == 2:
            hour, minute = int(parts[0]), int(parts[1])
            next_time = now.replace(hour=hour, minute=minute, second=0)
            if next_time <= now:
                next_time = next_time.replace(day=now.day + 1)
            next_post = next_time.strftime("%d.%m.%Y %H:%M")
    
    await message.answer(
        f"📊 <b>Статус Utro Bot</b>\n\n"
        f"🤖 Бот: <b>активен</b>\n"
        f"📢 Канал: <code>{config.channel_id}</code>\n\n"
        f"<b>Настройки:</b>\n"
        f"• 🖼 Изображения: {'✅ Вкл' if settings.image_enabled else '❌ Выкл'}\n"
        f"• 🎨 Модель: <b>{settings.image_model}</b>\n"
        f"• 📝 Шаблон: <b>{settings.text_template}</b>\n"
        f"• 🍳 Рецепты: <b>{settings.recipe_type}</b>\n\n"
        f"<b>Автопостинг:</b>\n"
        f"• Статус: {'✅ Вкл' if settings.autopost_enabled else '❌ Выкл'}\n"
        f"• Утренний пост: {settings.morning_post_time or 'Не установлен'}\n"
        f"• Следующий пост: {next_post}",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message):
    """Show settings menu."""
    if not await admin_only(message):
        return
    
    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите параметр для изменения:",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard()
    )


@router.message(F.text == "ℹ️ Помощь")
async def btn_help(message: Message):
    """Show help."""
    await cmd_help(message)


# ============== Post from Image ==============

@router.message(F.text == "🖼 Пост из фото")
async def btn_post_from_image(message: Message, state: FSMContext):
    """Start post from image workflow."""
    if not await admin_only(message):
        return
    
    await state.set_state(PostStates.waiting_for_image)
    await message.answer(
        "📷 <b>Пост из фотографии</b>\n\n"
        "Отправьте мне фото блюда, и я создам пост на его основе.\n\n"
        "Фото должно быть:\n"
        "• 🍽 Качественным\n"
        "• 🥗 С едой в кадре\n"
        "• 📸 Хорошо освещённым",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_button()
    )


@router.message(PostStates.waiting_for_image, F.photo)
async def handle_image_for_post(message: Message, state: FSMContext, bot: Bot):
    """Handle received image for post creation."""
    # Get largest photo
    photo = message.photo[-1]
    
    status_msg = await message.answer("⏳ Анализирую изображение...")
    
    try:
        # Download photo
        file = await bot.get_file(photo.file_id)
        photo_data = await bot.download_file(file.file_path)
        image_bytes = photo_data.read()
        
        # Store image in state
        await state.update_data(image_bytes=image_bytes, file_id=photo.file_id)
        await state.set_state(PostStates.selecting_category)
        
        await status_msg.edit_text(
            "📷 Фото получено!\n\n"
            "Выберите категорию рецепта:",
            reply_markup=image_category_keyboard()
        )
    except Exception as e:
        logger.error(f"Image processing error: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка обработки: {e}")
        await state.clear()


@router.callback_query(PostStates.selecting_category, F.data.startswith("cat:"))
async def handle_category_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Handle category selection for image post."""
    if not await admin_only_callback(callback):
        return
    
    category = callback.data.split(":")[1]
    category_names = {
        "pp": "ПП (правильное питание)",
        "keto": "Кето",
        "culinary": "Кулинария",
        "breakfast": "Завтраки",
        "dessert": "Десерты"
    }
    
    await callback.message.edit_text(
        f"⏳ Создаю {category_names.get(category, category)} пост на основе фото..."
    )
    
    try:
        data = await state.get_data()
        image_bytes = data.get("image_bytes")
        
        if not image_bytes:
            await callback.message.edit_text("❌ Изображение не найдено. Попробуйте снова.")
            await state.clear()
            return
        
        # Generate post content based on image
        content = await analyze_image_for_post(image_bytes, category)
        
        if not content:
            await callback.message.edit_text("❌ Не удалось проанализировать изображение.")
            await state.clear()
            return
        
        # Format post text
        from services.post_service_v2 import _format_post_text, _get_quote_for_weekday
        from datetime import date
        
        today = date.today()
        quote = _get_quote_for_weekday(today.weekday())
        post_text = _format_post_text(today, quote, content)
        
        # Store post data
        post_data = {
            "post_text": post_text,
            "image_bytes": image_bytes,  # Use user's photo
            "content": content,
            "quote": quote,
            "date": today,
            "generated_at": datetime.now(),
            "from_user_image": True
        }
        
        post_id = store_pending_post(post_data)
        
        # Send preview
        await send_preview_to_admin(
            bot=bot,
            admin_id=callback.from_user.id,
            post_data=post_data,
            reply_markup=preview_post_keyboard(post_id)
        )
        
        await callback.message.delete()
        await state.clear()
        
    except Exception as e:
        logger.error(f"Image post generation error: {e}", exc_info=True)
        await callback.message.edit_text(f"❌ Ошибка: {e}")
        await state.clear()


@router.message(PostStates.waiting_for_image)
async def handle_non_image(message: Message, state: FSMContext):
    """Handle non-image messages in waiting state."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "✅ Отменено",
            reply_markup=main_menu_keyboard()
        )
        return
    
    await message.answer(
        "⚠️ Пожалуйста, отправьте фотографию или нажмите Отмена",
        reply_markup=cancel_button()
    )


# ============== Settings Callbacks ==============

@router.callback_query(F.data == "settings:image_toggle")
async def settings_image_toggle(callback: CallbackQuery):
    """Toggle image generation."""
    if not await admin_only_callback(callback):
        return
    
    settings = get_settings()
    new_value = not settings.image_enabled
    update_settings(image_enabled=new_value)
    
    await callback.answer(f"Изображения: {'✅ Вкл' if new_value else '❌ Выкл'}")
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings:model_select")
async def settings_model_select(callback: CallbackQuery):
    """Show model selection."""
    if not await admin_only_callback(callback):
        return
    
    await callback.message.edit_text(
        "🎨 <b>Выбор модели генерации изображений</b>\n\n"
        "• <b>DALL-E 3</b> - Высокое качество, OpenAI\n"
        "• <b>Flux</b> - Быстрая генерация, Together AI\n\n"
        "Выберите модель:",
        parse_mode=ParseMode.HTML,
        reply_markup=model_select_keyboard()
    )


@router.callback_query(F.data.startswith("model:"))
async def handle_model_selection(callback: CallbackQuery):
    """Handle model selection."""
    if not await admin_only_callback(callback):
        return
    
    model = callback.data.split(":")[1]
    update_settings(image_model=model)
    
    await callback.answer(f"Модель: {model}")
    await callback.message.edit_text(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите параметр для изменения:",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard()
    )


@router.callback_query(F.data == "settings:template_select")
async def settings_template_select(callback: CallbackQuery):
    """Show template selection."""
    if not await admin_only_callback(callback):
        return
    
    await callback.message.edit_text(
        "📝 <b>Выбор шаблона текста</b>\n\n"
        "• <b>Короткий</b> (~800 символов) - Компактный пост\n"
        "• <b>Средний</b> (~1024 символа) - Стандартный пост\n"
        "• <b>Длинный</b> (~4096 символов) - Подробный пост\n"
        "• <b>Кастомный</b> - Ваш собственный шаблон\n\n"
        "Выберите шаблон:",
        parse_mode=ParseMode.HTML,
        reply_markup=template_select_keyboard()
    )


@router.callback_query(F.data.startswith("template:"))
async def handle_template_selection(callback: CallbackQuery, state: FSMContext):
    """Handle template selection."""
    if not await admin_only_callback(callback):
        return
    
    template = callback.data.split(":")[1]
    
    if template == "CUSTOM":
        await state.set_state(PostStates.waiting_custom_template)
        await callback.message.edit_text(
            "📝 <b>Кастомный шаблон</b>\n\n"
            "Отправьте шаблон текста с плейсхолдерами:\n\n"
            "<code>{greeting}</code> - Приветствие\n"
            "<code>{date}</code> - Дата\n"
            "<code>{weekday}</code> - День недели\n"
            "<code>{quote_text}</code> - Цитата\n"
            "<code>{quote_author}</code> - Автор цитаты\n"
            "<code>{holidays}</code> - Праздники\n"
            "<code>{recipe_name}</code> - Название рецепта\n"
            "<code>{ingredients}</code> - Ингредиенты\n"
            "<code>{instructions}</code> - Инструкция\n"
            "<code>{tip}</code> - Совет\n\n"
            "Пример:\n"
            "<code>{greeting}\n\n{holidays}\n\n{recipe_name}\n{ingredients}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_button()
        )
        return
    
    update_settings(text_template=template)
    await callback.answer(f"Шаблон: {template}")
    await callback.message.edit_text(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите параметр для изменения:",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard()
    )


@router.message(PostStates.waiting_custom_template)
async def handle_custom_template(message: Message, state: FSMContext):
    """Handle custom template input."""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "⚙️ <b>Настройки бота</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=settings_keyboard()
        )
        return
    
    # Validate template has some placeholders
    template = message.text
    placeholders = ["{greeting}", "{date}", "{recipe_name}", "{ingredients}"]
    has_placeholder = any(p in template for p in placeholders)
    
    if not has_placeholder:
        await message.answer(
            "⚠️ Шаблон должен содержать хотя бы один плейсхолдер.\n"
            "Попробуйте ещё раз или нажмите Отмена.",
            reply_markup=cancel_button()
        )
        return
    
    update_settings(text_template=TextTemplate.CUSTOM.value, custom_template=template)
    await state.clear()
    
    await message.answer(
        "✅ Кастомный шаблон сохранён!\n\n"
        "⚙️ <b>Настройки бота</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard()
    )


@router.callback_query(F.data == "settings:recipe_type")
async def settings_recipe_type(callback: CallbackQuery):
    """Toggle recipe type."""
    if not await admin_only_callback(callback):
        return
    
    settings = get_settings()
    types = [RecipeType.PP.value, RecipeType.KETO.value, RecipeType.MIXED.value]
    current_idx = types.index(settings.recipe_type) if settings.recipe_type in types else 0
    new_type = types[(current_idx + 1) % len(types)]
    
    update_settings(recipe_type=new_type)
    await callback.answer(f"Рецепты: {new_type}")
    await callback.message.edit_reply_markup(reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    """Back to main menu."""
    if not await admin_only_callback(callback):
        return
    
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard()
    )


# ============== Preview Callbacks ==============

@router.callback_query(F.data.startswith("publish:"))
async def handle_publish(callback: CallbackQuery, bot: Bot):
    """Publish pending post."""
    if not await admin_only_callback(callback):
        return
    
    post_id = callback.data.split(":")[1]
    
    await callback.message.edit_caption(
        caption="⏳ Публикую в канал...",
        reply_markup=None
    )
    
    success = await publish_pending_post(bot, post_id, config.channel_id)
    
    if success:
        await callback.message.edit_caption(
            caption="✅ Опубликовано в канал!",
            reply_markup=None
        )
        await asyncio.sleep(2)
        await callback.message.delete()
        await bot.send_message(
            callback.from_user.id,
            "✅ Пост успешно опубликован!",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.message.edit_caption(
            caption="❌ Ошибка публикации. Попробуйте снова.",
            reply_markup=preview_post_keyboard(post_id)
        )


@router.callback_query(F.data.startswith("edit:"))
async def handle_edit(callback: CallbackQuery, state: FSMContext):
    """Start editing post text."""
    if not await admin_only_callback(callback):
        return
    
    post_id = callback.data.split(":")[1]
    post_data = get_pending_post(post_id)
    
    if not post_data:
        await callback.answer("Пост не найден", show_alert=True)
        return
    
    # Store editing state
    start_editing(
        user_id=callback.from_user.id,
        post_id=post_id,
        message_id=callback.message.message_id,
        original_text=post_data.get("post_text", "")
    )
    
    await state.set_state(PostStates.editing_text)
    await state.update_data(post_id=post_id, preview_msg_id=callback.message.message_id)
    
    await callback.message.answer(
        "✏️ <b>Режим редактирования</b>\n\n"
        "Отправьте новый текст поста целиком.\n\n"
        "Текущий текст будет заменён на ваш.\n"
        "Для отмены нажмите кнопку ниже.",
        parse_mode=ParseMode.HTML,
        reply_markup=editing_keyboard()
    )
    await callback.answer()


@router.message(PostStates.editing_text)
async def handle_edit_text(message: Message, state: FSMContext, bot: Bot):
    """Handle new text during editing."""
    user_id = message.from_user.id
    
    # Check for cancel
    if message.text == "❌ Отмена редактирования":
        cancel_editing(user_id)
        await state.clear()
        await message.answer(
            "✅ Редактирование отменено. Пост не изменён.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Get editing state
    data = await state.get_data()
    post_id = data.get("post_id")
    preview_msg_id = data.get("preview_msg_id")
    
    if not post_id:
        await state.clear()
        await message.answer("❌ Сессия редактирования истекла.")
        return
    
    # Update post text
    new_text = message.text
    result = finish_editing(user_id, new_text)
    
    if result:
        await state.clear()
        await message.answer(
            "✅ Текст обновлён! Проверьте превью выше.",
            reply_markup=main_menu_keyboard()
        )
        
        # Update preview message
        post_data = get_pending_post(post_id)
        if post_data:
            try:
                preview_text = "📝 <b>Предпросмотр поста (обновлено):</b>\n\n" + new_text
                if post_data.get("image_bytes"):
                    await bot.edit_message_caption(
                        chat_id=user_id,
                        message_id=preview_msg_id,
                        caption=preview_text[:1024],
                        parse_mode=ParseMode.HTML,
                        reply_markup=preview_post_keyboard(post_id)
                    )
                else:
                    await bot.edit_message_text(
                        chat_id=user_id,
                        message_id=preview_msg_id,
                        text=preview_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=preview_post_keyboard(post_id)
                    )
            except Exception as e:
                logger.warning(f"Could not update preview: {e}")
    else:
        await message.answer("❌ Не удалось обновить текст. Попробуйте снова.")


@router.callback_query(F.data.startswith("regenerate:"))
async def handle_regenerate(callback: CallbackQuery, bot: Bot):
    """Regenerate post content."""
    if not await admin_only_callback(callback):
        return
    
    post_id = callback.data.split(":")[1]
    
    await callback.message.edit_caption(
        caption="⏳ Перегенерирую пост...",
        reply_markup=None
    )
    
    try:
        # Generate new post
        post_data = await generate_post_data()
        
        if post_data:
            # Store with same ID (replace)
            from services.post_service_v2 import _pending_posts
            _pending_posts[post_id] = post_data
            
            # Send new preview
            await send_preview_to_admin(
                bot=bot,
                admin_id=callback.from_user.id,
                post_data=post_data,
                reply_markup=preview_post_keyboard(post_id)
            )
            await callback.message.delete()
        else:
            await callback.message.edit_caption(
                caption="❌ Ошибка регенерации",
                reply_markup=preview_post_keyboard(post_id)
            )
    except Exception as e:
        logger.error(f"Regenerate error: {e}", exc_info=True)
        await callback.message.edit_caption(
            caption=f"❌ Ошибка: {e}",
            reply_markup=preview_post_keyboard(post_id)
        )


@router.callback_query(F.data.startswith("cancel:"))
async def handle_cancel_post(callback: CallbackQuery):
    """Cancel and discard post."""
    if not await admin_only_callback(callback):
        return
    
    post_id = callback.data.split(":")[1]
    from services.post_service_v2 import remove_pending_post
    remove_pending_post(post_id)
    
    await callback.message.delete()
    await callback.message.answer(
        "🗑 Пост отменён",
        reply_markup=main_menu_keyboard()
    )


# ============== Cancel State ==============

@router.callback_query(F.data == "cancel_action")
async def handle_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Universal cancel handler for any state."""
    if not await admin_only_callback(callback):
        return
    
    # Clear any editing state
    cancel_editing(callback.from_user.id)
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Действие отменено",
        reply_markup=None
    )
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "❌ Отмена")
async def handle_text_cancel(message: Message, state: FSMContext):
    """Handle text cancel button."""
    if not await admin_only(message):
        return
    
    cancel_editing(message.from_user.id)
    await state.clear()
    
    await message.answer(
        "✅ Отменено",
        reply_markup=main_menu_keyboard()
    )


@router.message(F.text == "❌ Отмена редактирования")
async def handle_edit_cancel(message: Message, state: FSMContext):
    """Handle edit cancel button."""
    if not await admin_only(message):
        return
    
    cancel_editing(message.from_user.id)
    await state.clear()
    
    await message.answer(
        "✅ Редактирование отменено",
        reply_markup=main_menu_keyboard()
    )


# ============== Command Shortcuts ==============

@router.message(Command("post"))
async def cmd_post(message: Message, bot: Bot):
    """Shortcut for today's post."""
    await btn_post_today(message, bot)


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Shortcut for settings."""
    await btn_settings(message)


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Shortcut for status."""
    await btn_status(message)


# ============== Fallback ==============

@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    """Handle unknown messages."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    current_state = await state.get_state()
    
    # If in some state, remind about cancel
    if current_state:
        await message.answer(
            "⚠️ Вы находитесь в режиме ввода.\n"
            "Завершите текущее действие или нажмите Отмена.",
            reply_markup=cancel_button()
        )
        return
    
    await message.answer(
        "🤔 Не понял команду.\n"
        "Используйте кнопки меню или /help",
        reply_markup=main_menu_keyboard()
    )
