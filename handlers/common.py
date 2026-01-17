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
☀️ <b>Добро пожаловать в Utro Bot!</b>

Я помогу вам публиковать ежедневные посты о кулинарных праздниках с ПП-рецептами.

<b>Используйте меню внизу:</b>
• ☀️ Утро сегодня — создать утренний пост
• ✨ Новый пост — создать свой пост
• 📊 Статус — информация о боте
• ⚙️ Настройки — параметры бота
• ❔ Помощь — справка
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
❔ <b>Справка по Utro Bot</b>

<b>О боте:</b>
Бот для публикации ежедневных постов о кулинарных праздниках с ПП-рецептами и AI-изображениями.

<b>Кнопки меню:</b>

☀️ <b>Утро сегодня</b>
Создать утренний пост с праздниками, рецептом и картинкой

✨ <b>Новый пост</b>
Создать пост с выбором категории:
• Рецепт — выбрать тип (ПП, Кето, Веган и др.)
• Свой — написать свою идею для поста

📊 <b>Статус</b>
Информация о боте и расписании

⚙️ <b>Настройки</b>
• Изображения — вкл/выкл генерацию
• Модель — DALL-E 3 или Flux
• Шаблон — длина поста
• Расписание — время автопостинга
• Тесты нейросетей

❔ <b>Помощь</b>
Эта справка
"""
    await message.answer(
        help_text, 
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


# ============================================
# REPLY KEYBOARD BUTTON HANDLERS
# ============================================

@router.message(F.text.in_({"☀️ Утро сегодня", "📅 Сегодня", "📨 Пост сейчас"}))
async def btn_post_today(message: Message) -> None:
    """Handle 'Утро сегодня' button - generate preview for today."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_post_today"
        )
        
        bot = message.bot
        
        await message.answer(
            "⏳ Генерирую утренний пост...\n\n"
            "Это может занять 1-2 минуты.",
            reply_markup=main_menu_keyboard()
        )
        
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} triggered today's post preview")
        
        from services.post_service import post_to_channel
        from keyboards import preview_post_keyboard
        
        success, post_id = await post_to_channel(
            bot=bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=user_id
        )
        
        if success and post_id:
            logger.info(f"Preview generated, post_id: {post_id}")
        else:
            await message.answer(
                "❌ Не удалось сгенерировать пост. Проверьте логи.",
                reply_markup=main_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in btn_post_today: {e}", exc_info=True)
        await message.answer(
            "⚠️ Ошибка при генерации поста.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text.in_({"✨ Новый пост", "🖼 Пост из фото"}))
async def btn_new_post(message: Message) -> None:
    """Handle 'Новый пост' button - start new post creation flow."""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await send_access_denied(message)
        return
    
    try:
        update_user_activity(
            user_id=user_id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            action="btn_new_post"
        )
        
        from keyboards import new_post_category_keyboard
        
        await message.answer(
            "✨ <b>Новый пост</b>\n\n"
            "Выберите тип поста:",
            parse_mode="HTML",
            reply_markup=new_post_category_keyboard()
        )
        
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} started new post flow")
        
    except Exception as e:
        logger.error(f"Error in btn_new_post: {e}", exc_info=True)
        await message.answer(
            "⚠️ Ошибка. Попробуйте позже.",
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
        
        from services.settings_service import get_settings
        
        settings = get_settings()
        img_status = "вкл" if settings.image_enabled else "выкл"
        model_name = settings.image_model
        template_name = settings.text_template
        
        settings_text = f"""
⚙️ <b>Настройки</b>

<b>Текущие параметры:</b>
🖼 Изображение: {img_status}
🎨 Модель: {model_name}
📝 Шаблон: {template_name}

Выберите настройку для изменения:
"""
        await message.answer(
            settings_text,
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        logger.info(f"{mask_user_id(user_id, config.debug_mode)} opened settings")
        
    except Exception as e:
        logger.error(f"Error in btn_settings: {e}", exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка.",
            reply_markup=main_menu_keyboard()
        )


@router.message(F.text.in_({"❔ Помощь", "ℹ️ Помощь"}))
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
