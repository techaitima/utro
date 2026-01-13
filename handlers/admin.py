"""
Admin handlers for bot management commands.
Handles /post_now, /status, /test_holidays commands.
"""

import logging
from datetime import datetime
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from config import config
from services.holidays_api import fetch_holidays_for_date
from services.post_service import post_to_channel

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Bot start time for uptime calculation
bot_start_time: datetime = datetime.now()
last_post_status: dict = {"success": None, "time": None, "error": None}


def set_bot_start_time(start_time: datetime) -> None:
    """Set the bot start time for uptime calculation."""
    global bot_start_time
    bot_start_time = start_time


def update_last_post_status(success: bool, error: str = None) -> None:
    """Update the last post status."""
    global last_post_status
    last_post_status = {
        "success": success,
        "time": datetime.now(),
        "error": error
    }


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.is_admin(user_id)


@router.message(Command("post_now"))
async def cmd_post_now(message: Message, bot: Bot) -> None:
    """
    Handle /post_now command - trigger immediate post to channel.
    Admin only.
    """
    try:
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав для выполнения этой команды.")
            logger.warning(f"Unauthorized access attempt to /post_now by user {message.from_user.id}")
            return
        
        await message.answer("⏳ Генерирую и отправляю пост в канал...\n\nЭто может занять 1-2 минуты.")
        logger.info(f"Admin {message.from_user.id} triggered manual post")
        
        # Trigger post
        success = await post_to_channel(bot, config.channel_id)
        
        if success:
            update_last_post_status(success=True)
            await message.answer("✅ Пост успешно опубликован в канал!")
            logger.info("Manual post completed successfully")
        else:
            update_last_post_status(success=False, error="Post failed")
            await message.answer("❌ Не удалось опубликовать пост. Проверьте логи для деталей.")
            logger.error("Manual post failed")
            
    except Exception as e:
        logger.error(f"Error in cmd_post_now: {e}", exc_info=True)
        update_last_post_status(success=False, error=str(e))
        await message.answer(f"❌ Произошла ошибка: {str(e)[:200]}")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """
    Handle /status command - show bot status and next post time.
    Admin only.
    """
    try:
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав для выполнения этой команды.")
            logger.warning(f"Unauthorized access attempt to /status by user {message.from_user.id}")
            return
        
        # Calculate uptime
        uptime = datetime.now() - bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}д {hours}ч {minutes}м {seconds}с"
        
        # Next post time
        now = datetime.now()
        post_hour = config.get_post_hour()
        post_minute = config.get_post_minute()
        
        next_post = now.replace(hour=post_hour, minute=post_minute, second=0, microsecond=0)
        if next_post <= now:
            next_post = next_post.replace(day=next_post.day + 1)
        
        time_until = next_post - now
        hours_until, remainder = divmod(time_until.seconds, 3600)
        minutes_until, _ = divmod(remainder, 60)
        
        # Last post status
        if last_post_status["time"]:
            last_post_time = last_post_status["time"].strftime("%d.%m.%Y %H:%M:%S")
            last_post_result = "✅ Успешно" if last_post_status["success"] else f"❌ Ошибка"
            if last_post_status["error"]:
                last_post_result += f"\n   └ {last_post_status['error'][:100]}"
        else:
            last_post_time = "Нет данных"
            last_post_result = "Нет данных"
        
        status_text = f"""
📊 <b>Статус бота</b>

<b>⏱ Аптайм:</b> {uptime_str}
<b>🕐 Время запуска:</b> {bot_start_time.strftime("%d.%m.%Y %H:%M:%S")}

<b>📅 Следующий пост:</b>
• Время: {next_post.strftime("%d.%m.%Y %H:%M")} (МСК)
• Через: {hours_until}ч {minutes_until}м

<b>📤 Последний пост:</b>
• Время: {last_post_time}
• Результат: {last_post_result}

<b>⚙️ Конфигурация:</b>
• Канал: {config.channel_id}
• Timezone: {config.timezone}
• Время поста: {config.morning_post_time}
• Админов: {len(config.admin_user_ids)}
• Holidays API: {"✅" if config.holidays_api_key else "❌"}
"""
        await message.answer(status_text, parse_mode="HTML")
        logger.info(f"Admin {message.from_user.id} checked status")
        
    except Exception as e:
        logger.error(f"Error in cmd_status: {e}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка: {str(e)[:200]}")


@router.message(Command("test_holidays"))
async def cmd_test_holidays(message: Message) -> None:
    """
    Handle /test_holidays command - fetch and display today's holidays.
    Admin only. For debugging API integration.
    """
    try:
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав для выполнения этой команды.")
            logger.warning(f"Unauthorized access attempt to /test_holidays by user {message.from_user.id}")
            return
        
        await message.answer("🔍 Запрашиваю праздники на сегодня...")
        logger.info(f"Admin {message.from_user.id} testing holidays API")
        
        today = datetime.now().date()
        holidays = await fetch_holidays_for_date(today)
        
        if holidays:
            holidays_text = f"🎉 <b>Праздники на {today.strftime('%d.%m.%Y')}:</b>\n\n"
            
            for i, holiday in enumerate(holidays, 1):
                name = holiday.get("name", "Без названия")
                description = holiday.get("description", "")
                holiday_type = holiday.get("type", "observance")
                
                holidays_text += f"{i}. <b>{name}</b>\n"
                if description:
                    holidays_text += f"   {description[:150]}...\n" if len(description) > 150 else f"   {description}\n"
                holidays_text += f"   <i>Тип: {holiday_type}</i>\n\n"
            
            holidays_text += f"✅ Всего найдено: {len(holidays)} праздников"
        else:
            holidays_text = """
❌ <b>Праздники не найдены</b>

Возможные причины:
• API ключ не настроен или недействителен
• Нет праздников на эту дату
• Проблема с подключением к API

Бот использует fallback генерацию через GPT-4o mini.
"""
        
        await message.answer(holidays_text, parse_mode="HTML")
        logger.info(f"Holidays test completed: {len(holidays)} holidays found")
        
    except Exception as e:
        logger.error(f"Error in cmd_test_holidays: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при запросе праздников: {str(e)[:200]}")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """
    Handle /admin command - show admin help.
    Admin only.
    """
    try:
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав для выполнения этой команды.")
            return
        
        admin_help = """
🔐 <b>Админ-команды</b>

/post_now — Отправить пост прямо сейчас
/status — Статус бота и следующий пост
/test_holidays — Проверить API праздников
/admin — Эта справка

<b>Горячие советы:</b>
• Используйте /test_holidays для диагностики API
• Проверяйте логи: <code>journalctl -u utro-bot -f</code>
• Перезапуск: <code>systemctl restart utro-bot</code>
"""
        await message.answer(admin_help, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in cmd_admin: {e}", exc_info=True)
        await message.answer("Произошла ошибка.")
