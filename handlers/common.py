"""
Common handlers for commands and menu buttons.
Handles /start, /help and persistent menu buttons.
All handlers check authorization first.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import config
from keyboards import main_menu_keyboard, settings_keyboard
from services.user_service import update_user_activity
from utils.logger import mask_user_id

logger = logging.getLogger(__name__)
router = Router(name="common")


def is_admin(user_id: int) -> bool:
    """Check if user is authorized admin."""
    return config.is_admin(user_id)


async def send_access_denied(message: Message) -> None:
    """Send access denied message to unauthorized users."""
    await message.answer(
        "❌ <b>У вас нет доступа к боту</b>\n\n"
        "Этот бот доступен только для администраторов.",
        parse_mode="HTML"
    )
    logger.warning(f"Unauthorized access attempt from {mask_user_id(message.from_user.id, config.debug_mode)}")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handle /start command - welcome message with main menu."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        # Update user activity
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="/start"
        )
        
        welcome_text = """
🍽 <b>Добро пожаловать в Utro Bot!</b>

Я ваш персональный помощник по кулинарным праздникам! 🎉

<b>Что я умею:</b>
• 📅 Каждое утро публикую информацию о праздниках еды
• 🥗 Генерирую ПП-рецепты (правильное питание)
• 🤖 Использую AI для создания уникального контента
• 🎨 Создаю красивые изображения блюд

<b>Используйте меню внизу для управления ботом:</b>
• 📨 Пост сейчас — отправить пост в канал
• 📊 Статус — информация о работе бота
• ⚙️ Настройки — настройки и тесты
• ℹ️ Помощь — справка по боту
"""
        await message.answer(
            welcome_text, 
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} started the bot")
        
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command - bot description and features."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="/help"
        )
        
        await show_help(message)
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} requested help")
        
    except Exception as e:
        logger.error(f"Error in cmd_help: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu_keyboard()
        )


async def show_help(message: Message) -> None:
    """Display help text."""
    help_text = """
📚 <b>Справка по Utro Bot</b>

<b>О боте:</b>
Этот бот автоматически публикует ежедневные посты о кулинарных праздниках с ПП-рецептами.

<b>Расписание:</b>
📅 Посты публикуются каждый день в 8:00 по московскому времени

<b>Что включает каждый пост:</b>
• ☀️ Доброе утро с мотивирующей цитатой
• 🎉 Информация о праздниках еды сегодня
• 🥗 Полезный рецепт без сахара
• 🖼 Красивое изображение блюда

<b>Кнопки меню:</b>
• 📨 <b>Пост сейчас</b> — немедленная отправка поста в канал
• 📊 <b>Статус</b> — информация о боте и следующем посте
• ⚙️ <b>Настройки</b> — тесты API и настройка расписания
• ℹ️ <b>Помощь</b> — эта справка

<b>Команды:</b>
/start — Главное меню
/help — Справка
/post_now — Отправить пост сейчас
/status — Статус бота
"""
    await message.answer(
        help_text, 
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


# ============================================
# REPLY KEYBOARD BUTTON HANDLERS
# ============================================

@router.message(F.text == "📨 Пост сейчас")
async def btn_post_now(message: Message) -> None:
    """Handle 'Пост сейчас' button - generate preview for admin."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_post_now"
        )
        
        # Get bot instance from message
        bot = message.bot
        
        await message.answer(
            "⏳ Генерирую пост...\n\n"
            "Это может занять 1-2 минуты.",
            reply_markup=main_menu_keyboard()
        )
        
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} triggered post preview via button")
        
        # Generate preview instead of posting directly
        from services.post_service import post_to_channel
        from keyboards import preview_post_keyboard
        
        success, post_id = await post_to_channel(
            bot=bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=user_id
        )
        
        if success and post_id:
            logger.info(f"Preview generated for {mask_user_id(user_id, config.debug_mode)}, post_id: {post_id}")
            # Preview already sent by post_to_channel
        else:
            await message.answer(
                "❌ Не удалось сгенерировать пост. Проверьте логи.",
                reply_markup=main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in btn_post_now: {e}", exc_info=True)
        await message.answer(
            f"⚠️ Произошла ошибка: {str(e)[:100]}",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "📊 Статус")
async def btn_status(message: Message) -> None:
    """Handle 'Статус' button - show bot status."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_status"
        )
        
        # Reuse admin status command logic
        from handlers.admin import cmd_status
        await cmd_status(message)
        
    except Exception as e:
        logger.error(f"Error in btn_status: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка при получении статуса.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message) -> None:
    """Handle 'Настройки' button - show settings menu."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_settings"
        )
        
        settings_text = """
⚙️ <b>Настройки и тесты</b>

Выберите действие:

• <b>Расписание</b> — настройка времени постинга
• <b>Тест DALL-E</b> — сгенерировать тестовое изображение
• <b>Тест праздников</b> — проверить API праздников
• <b>Тест GPT-4o mini</b> — сгенерировать тестовый контент
• <b>Моя статистика</b> — ваша активность в боте
"""
        await message.answer(
            settings_text,
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} opened settings"))
        
    except Exception as e:
        logger.error(f"Error in btn_settings: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text == "ℹ️ Помощь")
async def btn_help(message: Message) -> None:
    """Handle 'Помощь' button - show help."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_help"
        )
        
        await show_help(message)
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} requested help via button")
        
    except Exception as e:
        logger.error(f"Error in btn_help: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=main_menu_keyboard()
        )


# ============================================
# CATCH-ALL HANDLER FOR UNAUTHORIZED MESSAGES
# ============================================

@router.message()
async def catch_all(message: Message) -> None:
    """Catch all other messages - check auth and show menu."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    # For authorized users, show the menu
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте кнопки меню внизу или отправьте /help",
        reply_markup=main_menu_keyboard()
    )
