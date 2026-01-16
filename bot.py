"""
Utro Bot - Main Entry Point

Telegram bot that posts daily food holidays with AI-generated PP recipes.
Uses GPT-4o mini for content generation and DALL-E 3 for images.

Author: Utro Bot Team
License: MIT
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent

from config import config
from handlers import admin_router, common_router, callbacks_router
from handlers.admin import set_bot_start_time, update_last_post_status
from services.scheduler import start_scheduler, stop_scheduler
from services.post_service import post_to_channel
from services.user_service import ensure_data_file_exists

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Reduce noise from third-party libraries
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.INFO)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global bot instance for scheduler access
bot_instance: Bot = None


async def scheduled_morning_post() -> None:
    """
    Scheduled job function for morning posts.
    Called by APScheduler at configured time.
    Posts DIRECTLY to channel without preview (scheduled posts).
    """
    global bot_instance
    
    logger.info("=== Starting scheduled morning post ===")
    
    try:
        # preview_mode=False for scheduled posts - publish directly
        success, _ = await post_to_channel(
            bot=bot_instance, 
            channel_id=config.channel_id,
            preview_mode=False  # Direct publish for scheduler
        )
        update_last_post_status(success=success)
        
        if success:
            logger.info("=== Scheduled post completed successfully ===")
        else:
            logger.error("=== Scheduled post failed ===")
            
    except Exception as e:
        logger.error(f"=== Scheduled post error: {e} ===", exc_info=True)
        update_last_post_status(success=False, error=str(e))


async def on_startup(bot: Bot) -> None:
    """
    Called when bot starts.
    Initializes scheduler, user data file, and logs startup info.
    """
    global bot_instance
    bot_instance = bot
    
    # Ensure user data file exists
    ensure_data_file_exists()
    
    logger.info("=" * 50)
    logger.info("🤖 Utro Bot starting...")
    logger.info(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📢 Channel ID: {config.channel_id}")
    logger.info(f"🕐 Timezone: {config.timezone}")
    logger.info(f"⏰ Morning post time: {config.morning_post_time}")
    logger.info(f"👤 Admin users: {len(config.admin_user_ids)}")
    logger.info(f"🎉 Holidays API: {'✅ Configured' if config.holidays_api_key else '❌ Not configured'}")
    logger.info("=" * 50)
    
    # Set bot start time for uptime tracking
    set_bot_start_time(datetime.now())
    
    # Start the scheduler
    start_scheduler(scheduled_morning_post)
    logger.info("✅ Scheduler started successfully")
    
    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"🤖 Bot username: @{bot_info.username}")
        logger.info(f"🆔 Bot ID: {bot_info.id}")
    except Exception as e:
        logger.warning(f"Could not get bot info: {e}")


async def on_shutdown(bot: Bot) -> None:
    """
    Called when bot shuts down.
    Stops scheduler and cleans up resources.
    """
    logger.info("=" * 50)
    logger.info("🛑 Shutting down Utro Bot...")
    logger.info(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Stop the scheduler
    stop_scheduler()
    logger.info("✅ Scheduler stopped")
    
    # Close bot session
    await bot.session.close()
    logger.info("✅ Bot session closed")
    
    logger.info("🛑 Bot shutdown complete")
    logger.info("=" * 50)


def handle_signal(sig, frame):
    """Handle termination signals for graceful shutdown."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    sys.exit(0)


async def main() -> None:
    """
    Main function - entry point for the bot.
    Sets up bot, dispatcher, handlers, error handler, and starts polling.
    """
    # Validate configuration
    logger.info("Validating configuration...")
    
    # Create bot instance with default properties
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register global error handler
    @dp.error()
    async def error_handler(event: ErrorEvent) -> bool:
        """
        Global error handler for all unhandled exceptions.
        Logs the error and prevents bot crash.
        """
        logger.error(
            f"Error handling update: {event.exception}",
            exc_info=event.exception
        )
        
        # Try to notify user about the error
        try:
            if event.update.message:
                await event.update.message.answer(
                    "⚠️ Произошла ошибка. Администратор уведомлен.\n\n"
                    "Попробуйте позже или используйте /start"
                )
            elif event.update.callback_query:
                await event.update.callback_query.answer(
                    "⚠️ Произошла ошибка",
                    show_alert=True
                )
        except Exception as notify_error:
            logger.error(f"Could not notify user about error: {notify_error}")
        
        # Return True to prevent the error from propagating
        return True
    
    # Register routers (order matters - callbacks before common for catch-all)
    dp.include_router(admin_router)
    dp.include_router(callbacks_router)
    dp.include_router(common_router)
    logger.info("✅ Routers registered: admin, callbacks, common")
    
    # Register startup and shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        logger.info("Starting bot polling...")
        
        # Delete webhook before polling (in case it was set)
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Start polling
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=False
        )
        
    except Exception as e:
        logger.error(f"Bot polling error: {e}", exc_info=True)
        raise
    finally:
        await on_shutdown(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
