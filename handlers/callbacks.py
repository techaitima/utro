"""
Callback handlers for inline keyboard buttons.
Handles all callback queries from inline keyboards.
"""

import logging
from datetime import datetime, date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, BufferedInputFile

from config import config
from keyboards import (
    main_menu_keyboard, 
    settings_keyboard, 
    schedule_keyboard,
    back_keyboard
)
from services.user_service import update_user_activity, format_user_stats
from utils.logger import mask_user_id, mask_channel_id

logger = logging.getLogger(__name__)
router = Router(name="callbacks")


def is_admin(user_id: int) -> bool:
    """Check if user is authorized admin."""
    return config.is_admin(user_id)


async def answer_unauthorized(callback: CallbackQuery) -> None:
    """Answer callback for unauthorized users."""
    await callback.answer("❌ У вас нет доступа", show_alert=True)
    logger.warning(f"Unauthorized callback from {mask_user_id(callback.from_user.id, config.debug_mode)}")


# ============================================
# SETTINGS MENU CALLBACKS
# ============================================

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery) -> None:
    """Handle 'Назад' button from settings - return to main menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_back_main"
        )
        
        main_text = """
🍽 <b>Utro Bot</b>

Используйте кнопки меню для управления ботом.

• 📨 <b>Пост сейчас</b> — отправить пост в канал
• 📊 <b>Статус</b> — информация о боте
• ⚙️ <b>Настройки</b> — настройки и тесты
• ℹ️ <b>Помощь</b> — справка
"""
        await callback.message.edit_text(
            main_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in cb_back_main: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_settings")
async def cb_back_settings(callback: CallbackQuery) -> None:
    """Handle 'Назад' button - return to settings menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        settings_text = """
⚙️ <b>Настройки и тесты</b>

Выберите действие:

• <b>Расписание</b> — настройка времени постинга
• <b>Тест DALL-E</b> — сгенерировать тестовое изображение
• <b>Тест праздников</b> — проверить API праздников
• <b>Тест GPT-4o mini</b> — сгенерировать тестовый контент
• <b>Моя статистика</b> — ваша активность в боте
"""
        await callback.message.edit_text(
            settings_text,
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_back_settings: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "schedule")
async def cb_schedule(callback: CallbackQuery) -> None:
    """Handle 'Расписание' button - show schedule settings."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_schedule"
        )
        
        current_time = config.morning_post_time
        schedule_text = f"""
⏰ <b>Расписание постинга</b>

<b>Текущее время:</b> {current_time} (МСК)
<b>Часовой пояс:</b> {config.timezone}

Выберите новое время для ежедневных постов:

⚠️ <i>Изменение времени требует перезапуска бота. 
Для изменения отредактируйте MORNING_POST_TIME в .env файле.</i>
"""
        await callback.message.edit_text(
            schedule_text,
            parse_mode="HTML",
            reply_markup=schedule_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_schedule: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("set_time_"))
async def cb_set_time(callback: CallbackQuery) -> None:
    """Handle time selection buttons."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        hour = callback.data.replace("set_time_", "")
        await callback.answer(
            f"⏰ Для изменения времени на {hour}:00 отредактируйте .env файл:\n"
            f"MORNING_POST_TIME={hour}:00",
            show_alert=True
        )
        
    except Exception as e:
        logger.error(f"Error in cb_set_time: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# TEST CALLBACKS
# ============================================

@router.callback_query(F.data == "test_holidays")
async def cb_test_holidays(callback: CallbackQuery) -> None:
    """Handle 'Тест праздников' button - test holidays API."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🔍 Загружаю праздники...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_holidays"
        )
        
        # Show loading state
        await callback.message.edit_text(
            "🔍 <b>Загружаю праздники...</b>\n\nЭто может занять несколько секунд.",
            parse_mode="HTML"
        )
        
        # Fetch holidays
        from services.holidays_api import fetch_holidays_for_date
        today = date.today()
        holidays = await fetch_holidays_for_date(today)
        
        if holidays:
            holidays_text = f"🎉 <b>Праздники на {today.strftime('%d.%m.%Y')}:</b>\n\n"
            
            for i, holiday in enumerate(holidays[:10], 1):
                name = holiday.get("name", "Без названия")
                holidays_text += f"{i}. {name}\n"
            
            holidays_text += f"\n✅ <b>Всего найдено:</b> {len(holidays)} праздников"
            holidays_text += f"\n\n<i>API работает корректно!</i>"
        else:
            holidays_text = """
❌ <b>Праздники не найдены</b>

Возможные причины:
• API ключ не настроен
• Нет праздников на сегодня
• Проблема с подключением

<i>Бот использует fallback через GPT-4o mini</i>
"""
        
        await callback.message.edit_text(
            holidays_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested holidays API: {len(holidays)} found")
        
    except Exception as e:
        logger.error(f"Error in cb_test_holidays: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка при тестировании:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )


@router.callback_query(F.data == "test_gpt")
async def cb_test_gpt(callback: CallbackQuery) -> None:
    """Handle 'Тест GPT-4o mini' button - test AI content generation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🤖 Генерирую контент...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_gpt"
        )
        
        await callback.message.edit_text(
            "🤖 <b>Генерирую тестовый контент...</b>\n\n"
            "Это может занять 10-30 секунд.",
            parse_mode="HTML"
        )
        
        # Generate content
        from services.ai_content import generate_greeting
        greeting = await generate_greeting()
        
        result_text = f"""
🤖 <b>Тест GPT-4o mini</b>

<b>Сгенерированное приветствие:</b>

{greeting}

✅ <i>AI работает корректно!</i>
"""
        
        await callback.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested GPT-4o mini")
        
    except Exception as e:
        logger.error(f"Error in cb_test_gpt: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка GPT-4o mini:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )


@router.callback_query(F.data == "test_dalle")
async def cb_test_dalle(callback: CallbackQuery) -> None:
    """Handle 'Тест DALL-E' button - generate test image."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🎨 Генерирую изображение...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_dalle"
        )
        
        await callback.message.edit_text(
            "🎨 <b>Генерирую тестовое изображение...</b>\n\n"
            "Это может занять 30-60 секунд.\n"
            "Стоимость: ~$0.04",
            parse_mode="HTML"
        )
        
        # Generate image
        from services.image_generator import generate_food_image
        image_bytes = await generate_food_image(
            recipe_name="Test Image",
            english_prompt="healthy colorful salad bowl, appetizing"
        )
        
        if image_bytes:
            # Send image
            photo = BufferedInputFile(image_bytes, filename="test_dalle.jpg")
            await callback.message.answer_photo(
                photo=photo,
                caption="🎨 <b>Тестовое изображение DALL-E 3</b>\n\n✅ Генерация работает корректно!",
                parse_mode="HTML"
            )
            
            # Edit original message
            await callback.message.edit_text(
                "✅ <b>Изображение сгенерировано!</b>\n\n"
                "Смотрите выше ⬆️",
                parse_mode="HTML",
                reply_markup=back_keyboard()
            )
            
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested DALL-E 3 successfully")
        else:
            await callback.message.edit_text(
                "❌ <b>Не удалось сгенерировать изображение</b>\n\n"
                "Проверьте баланс OpenAI и API ключ.",
                parse_mode="HTML",
                reply_markup=back_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in cb_test_dalle: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка DALL-E:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )


@router.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery) -> None:
    """Handle 'Моя статистика' button - show user stats."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_my_stats"
        )
        
        stats_text = format_user_stats(callback.from_user.id)
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} viewed their stats"))
        
    except Exception as e:
        logger.error(f"Error in cb_my_stats: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# POST CONFIRMATION CALLBACKS
# ============================================

@router.callback_query(F.data == "confirm_post")
async def cb_confirm_post(callback: CallbackQuery) -> None:
    """Handle post confirmation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("📤 Отправляю пост...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_confirm_post"
        )
        
        await callback.message.edit_text(
            "⏳ <b>Генерирую и отправляю пост...</b>\n\n"
            "Это может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        from services.post_service import post_to_channel
        from handlers.admin import update_last_post_status
        from services.user_service import increment_posts_triggered
        
        bot = callback.message.bot
        success = await post_to_channel(bot, config.channel_id)
        
        if success:
            update_last_post_status(success=True)
            increment_posts_triggered(callback.from_user.id)
            await callback.message.edit_text(
                "✅ <b>Пост успешно опубликован!</b>",
                parse_mode="HTML"
            )
        else:
            update_last_post_status(success=False, error="Post failed")
            await callback.message.edit_text(
                "❌ <b>Не удалось опубликовать пост.</b>\n\n"
                "Проверьте логи для деталей.",
                parse_mode="HTML"
            )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} confirmed post: {'success' if success else 'failed'}")
        
    except Exception as e:
        logger.error(f"Error in cb_confirm_post: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка:</b> {str(e)[:100]}",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "cancel_post")
async def cb_cancel_post(callback: CallbackQuery) -> None:
    """Handle post cancellation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("Отменено")
        
        await callback.message.edit_text(
            "❌ <b>Отправка поста отменена.</b>",
            parse_mode="HTML"
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} cancelled post")
        
    except Exception as e:
        logger.error(f"Error in cb_cancel_post: {e}", exc_info=True)


# ============================================
# LEGACY ADMIN CALLBACKS (for compatibility)
# ============================================

@router.callback_query(F.data == "admin_post_now")
async def cb_admin_post_now(callback: CallbackQuery) -> None:
    """Legacy callback for admin post button."""
    await cb_confirm_post(callback)


@router.callback_query(F.data == "admin_status")
async def cb_admin_status(callback: CallbackQuery) -> None:
    """Legacy callback for admin status button."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        # Import and call status logic
        from handlers.admin import bot_start_time, last_post_status
        
        uptime = datetime.now() - bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        status_text = f"""
📊 <b>Статус бота</b>

⏱ <b>Аптайм:</b> {days}д {hours}ч {minutes}м
📅 <b>Время поста:</b> {config.morning_post_time} (МСК)
📢 <b>Канал:</b> {mask_channel_id(config.channel_id, config.debug_mode)}
"""
        
        await callback.message.edit_text(
            status_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_admin_status: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_test_holidays")
async def cb_admin_test_holidays(callback: CallbackQuery) -> None:
    """Legacy callback for admin test holidays button."""
    await cb_test_holidays(callback)


# ============================================
# POST PREVIEW CALLBACKS
# ============================================

@router.callback_query(F.data.startswith("publish_post"))
async def cb_publish_post(callback: CallbackQuery) -> None:
    """Handle '✅ Опубликовать в канал' button - publish pending post."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("📤 Публикую в канал...")
        
        # Extract post_id from callback data
        parts = callback.data.split(":")
        post_id = parts[1] if len(parts) > 1 else ""
        
        if not post_id:
            await callback.message.edit_caption(
                caption="❌ <b>Ошибка:</b> Пост не найден.\n\nПопробуйте сгенерировать новый.",
                parse_mode="HTML"
            )
            return
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="publish_post"
        )
        
        # Publish the pending post
        from services.post_service import publish_pending_post
        from services.user_service import increment_posts_triggered
        from handlers.admin import update_last_post_status
        
        success = await publish_pending_post(
            bot=callback.bot,
            post_id=post_id,
            channel_id=config.channel_id
        )
        
        if success:
            update_last_post_status(success=True)
            increment_posts_triggered(callback.from_user.id)
            
            # Update the preview message
            await callback.message.edit_caption(
                caption="✅ <b>Пост успешно опубликован в канале!</b>",
                parse_mode="HTML"
            )
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} published post {post_id}")
        else:
            update_last_post_status(success=False, error="Publish failed")
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось опубликовать пост.</b>\n\nПроверьте логи для деталей.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in cb_publish_post: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при публикации", show_alert=True)


@router.callback_query(F.data.startswith("cancel_preview"))
async def cb_cancel_preview(callback: CallbackQuery) -> None:
    """Handle '❌ Отменить' button - cancel pending post."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("Отменено")
        
        # Extract post_id from callback data
        parts = callback.data.split(":")
        post_id = parts[1] if len(parts) > 1 else ""
        
        # Remove pending post if exists
        if post_id:
            from services.post_service import remove_pending_post
            remove_pending_post(post_id)
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cancel_preview"
        )
        
        # Update the preview message
        await callback.message.edit_caption(
            caption="❌ <b>Публикация отменена</b>\n\nИспользуйте меню для создания нового поста.",
            parse_mode="HTML"
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} cancelled preview"))
        
    except Exception as e:
        logger.error(f"Error in cb_cancel_preview: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("regenerate_post"))
async def cb_regenerate_post(callback: CallbackQuery) -> None:
    """Handle '🔄 Регенерировать' button - generate new post content."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🔄 Генерирую новый пост...")
        
        # Extract old post_id and remove it
        parts = callback.data.split(":")
        old_post_id = parts[1] if len(parts) > 1 else ""
        
        if old_post_id:
            from services.post_service import remove_pending_post
            remove_pending_post(old_post_id)
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="regenerate_post"
        )
        
        # Update message to show loading
        await callback.message.edit_caption(
            caption="🔄 <b>Генерирую новый пост...</b>\n\nЭто может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        # Generate new post with preview
        from services.post_service import post_to_channel
        from keyboards import preview_post_keyboard
        
        success, new_post_id = await post_to_channel(
            bot=callback.bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=callback.from_user.id
        )
        
        if success and new_post_id:
            # Delete the old message (new preview was sent)
            try:
                await callback.message.delete()
            except Exception:
                pass
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} regenerated post, new_id: {new_post_id}")
        else:
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось сгенерировать новый пост.</b>\n\nПопробуйте позже.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in cb_regenerate_post: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при регенерации", show_alert=True)


# ============================================
# CATCH-ALL CALLBACK HANDLER
# ============================================

@router.callback_query()
async def cb_unknown(callback: CallbackQuery) -> None:
    """Handle unknown callback queries."""
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)
    logger.warning(f"Unknown callback: {callback.data} from {mask_user_id(callback.from_user.id, config.debug_mode)}")
