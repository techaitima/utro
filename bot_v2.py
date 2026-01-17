"""
Utro Bot v2 - Main entry point.
Telegram bot for daily food holidays, PP/Keto recipes, and healthy morning posts.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import config
from handlers_v2 import router
from services.settings_service import get_settings, update_settings
from services.post_service_v2 import post_to_channel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Bot and dispatcher
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Scheduler for autoposting
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def scheduled_morning_post():
    """
    Scheduled job for morning autopost.
    Always generates with image (force_image=True).
    """
    logger.info("Running scheduled morning post...")
    settings = get_settings()
    
    if not settings.autopost_enabled:
        logger.info("Autopost is disabled, skipping")
        return
    
    try:
        # Force image generation for morning posts
        success, _ = await post_to_channel(
            bot=bot,
            channel_id=config.channel_id,
            max_retries=3,
            preview_mode=False,  # Direct publish, no preview
            force_image=True  # Always with image
        )
        
        if success:
            logger.info("Morning post published successfully")
            # Notify admin
            try:
                await bot.send_message(
                    config.admin_id,
                    "✅ Утренний пост опубликован автоматически!"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin: {e}")
        else:
            logger.error("Morning post failed")
            # Notify admin about failure
            try:
                await bot.send_message(
                    config.admin_id,
                    "❌ Ошибка автопубликации утреннего поста. "
                    "Проверьте логи и попробуйте вручную: /post"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin: {e}")
                
    except Exception as e:
        logger.error(f"Scheduled post error: {e}", exc_info=True)


def setup_scheduler():
    """
    Setup APScheduler with morning post job.
    Only morning posts are scheduled (with images).
    """
    settings = get_settings()
    
    if not settings.autopost_enabled:
        logger.info("Autopost disabled, scheduler not started")
        return
    
    if not settings.morning_post_time:
        logger.warning("No morning post time configured")
        return
    
    try:
        parts = settings.morning_post_time.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        
        # Morning post job
        scheduler.add_job(
            scheduled_morning_post,
            CronTrigger(hour=hour, minute=minute),
            id="morning_post",
            replace_existing=True,
            name="Morning Post"
        )
        
        logger.info(f"Scheduled morning post at {hour:02d}:{minute:02d}")
        
    except Exception as e:
        logger.error(f"Scheduler setup error: {e}")


async def on_startup():
    """Startup actions."""
    logger.info("=" * 50)
    logger.info("Utro Bot v2 starting...")
    logger.info(f"Admin ID: {config.admin_id}")
    logger.info(f"Channel: {config.channel_id}")
    
    # Get settings
    settings = get_settings()
    logger.info(f"Image model: {settings.image_model}")
    logger.info(f"Text template: {settings.text_template}")
    logger.info(f"Recipe type: {settings.recipe_type}")
    logger.info(f"Autopost: {'enabled' if settings.autopost_enabled else 'disabled'}")
    
    # Setup scheduler
    setup_scheduler()
    if settings.autopost_enabled:
        scheduler.start()
        logger.info("Scheduler started")
    
    # Notify admin
    try:
        await bot.send_message(
            config.admin_id,
            "🤖 <b>Utro Bot v2 запущен!</b>\n\n"
            f"📊 Модель: {settings.image_model}\n"
            f"📝 Шаблон: {settings.text_template}\n"
            f"🍳 Рецепты: {settings.recipe_type}\n"
            f"⏰ Автопост: {'✅' if settings.autopost_enabled else '❌'}\n\n"
            "Используйте /help для справки."
        )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")
    
    logger.info("Bot startup complete")
    logger.info("=" * 50)


async def on_shutdown():
    """Shutdown actions."""
    logger.info("Shutting down...")
    
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    
    await bot.session.close()
    logger.info("Bot session closed")


async def main():
    """Main entry point."""
    # Register handlers
    dp.include_router(router)
    
    # Register startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
