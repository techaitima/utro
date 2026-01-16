"""
Post service - main channel posting orchestration.
Coordinates holidays API, AI content generation, and channel posting.
"""

import json
import logging
import asyncio
import random
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup

from config import config
from services.holidays_api import fetch_holidays_for_date
from services.ai_content import generate_post_content, MONTHS_RU, WEEKDAYS_RU
from services.image_generator import generate_food_image

logger = logging.getLogger(__name__)

# Path to quotes file
QUOTES_FILE = Path(__file__).parent.parent / "data" / "quotes.json"

# Temporary storage for preview posts (post_id -> post_data)
_pending_posts: Dict[str, Dict[str, Any]] = {}

# Weekday mapping for quotes.json keys
WEEKDAY_KEYS = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}


def _load_quotes() -> Dict[str, list]:
    """Load quotes from JSON file."""
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Quotes file not found: {QUOTES_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing quotes file: {e}")
        return {}


def _get_quote_for_weekday(weekday: int) -> Dict[str, str]:
    """
    Get a random quote for the given weekday.
    
    Args:
        weekday: Day of week (0=Monday, 6=Sunday)
    
    Returns:
        Dictionary with 'text' and 'author' keys
    """
    quotes = _load_quotes()
    weekday_key = WEEKDAY_KEYS.get(weekday, "monday")
    
    day_quotes = quotes.get(weekday_key, [])
    if day_quotes:
        return random.choice(day_quotes)
    
    # Fallback quote
    return {
        "text": "Каждый день — это новая возможность стать лучше",
        "author": "Народная мудрость"
    }


def _format_post_text(
    target_date: date,
    quote: Dict[str, str],
    content: Dict[str, Any]
) -> str:
    """
    Format the full post text with HTML formatting.
    
    Args:
        target_date: Date of the post
        quote: Quote dictionary with 'text' and 'author'
        content: Generated content from AI
    
    Returns:
        Formatted HTML post text
    """
    # Extract content parts
    greeting = content.get("greeting", "Доброе утро, мои дорогие! ☀️")
    holiday_text = content.get("holiday_text", "")
    recipe = content.get("recipe", {})
    
    # Format date
    date_str = f"{target_date.day} {MONTHS_RU[target_date.month]}"
    
    # Format recipe
    recipe_name = recipe.get("name", "Полезное блюдо")
    servings = recipe.get("servings", 4)
    cooking_time = recipe.get("cooking_time", 30)
    ingredients = recipe.get("ingredients", [])
    instructions = recipe.get("instructions", [])
    tip = recipe.get("tip", "")
    
    # Build ingredients list
    ingredients_text = "\n".join([f"• {ing}" for ing in ingredients])
    
    # Build instructions list
    instructions_text = "\n".join([
        f"{i}. {step}" for i, step in enumerate(instructions, 1)
    ])
    
    # Build full post
    post_parts = [
        greeting,
        "",
        f"<i>«{quote['text']}»</i> — {quote['author']}",
        "",
        f"📅 Сегодня <b>{date_str}</b>",
        "",
        holiday_text,
        "",
        f"📖 <b>Рецепт: {recipe_name}</b>",
        "",
        f"🍽 Порции: {servings} | ⏱ Время: {cooking_time} минут",
        "",
        "<b>Ингредиенты:</b>",
        ingredients_text,
        "",
        "<b>Приготовление:</b>",
        instructions_text,
    ]
    
    # Add tip if present
    if tip:
        post_parts.extend(["", f"💡 <b>Совет:</b> {tip}"])
    
    return "\n".join(post_parts)


async def generate_post_data(
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Generate post content and image without publishing.
    
    Returns:
        Dictionary with post_text, image_bytes, content, quote, date
        or None if generation failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating post data (attempt {attempt}/{max_retries})")
            start_time = datetime.now()
            
            # Step 1: Get current date
            today = date.today()
            logger.info(f"Generating post for {today}")
            
            # Step 2: Fetch real holidays from API
            logger.info("Fetching holidays from API...")
            holidays = await fetch_holidays_for_date(today)
            logger.info(f"Found {len(holidays)} holidays")
            
            # Step 3: Get quote for today's weekday
            quote = _get_quote_for_weekday(today.weekday())
            logger.info(f"Selected quote by {quote['author']}")
            
            # Step 4: Generate AI content
            logger.info("Generating AI content...")
            content = await generate_post_content(today, holidays, quote)
            logger.info(f"Generated recipe: {content['recipe']['name']}")
            
            # Step 5: Format post text
            post_text = _format_post_text(today, quote, content)
            logger.info(f"Post text formatted ({len(post_text)} chars)")
            
            # Step 6: Generate image
            logger.info("Generating image with DALL-E 3...")
            recipe = content.get("recipe", {})
            image_prompt = recipe.get("image_prompt_en", recipe.get("name", "healthy food"))
            
            image_bytes = await generate_food_image(
                recipe_name=recipe.get("name", "Recipe"),
                english_prompt=image_prompt
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Post data generated in {execution_time:.1f}s")
            
            return {
                "post_text": post_text,
                "image_bytes": image_bytes,
                "content": content,
                "quote": quote,
                "date": today,
                "generated_at": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Post data generation attempt {attempt} failed: {e}", exc_info=True)
            if attempt >= max_retries:
                logger.error(f"All {max_retries} attempts failed")
                return None
            await asyncio.sleep(5)
    
    return None


def store_pending_post(post_data: Dict[str, Any]) -> str:
    """
    Store post data for later publishing.
    
    Args:
        post_data: Generated post data
        
    Returns:
        Unique post_id for retrieval
    """
    post_id = str(uuid.uuid4())[:8]
    _pending_posts[post_id] = post_data
    logger.info(f"Stored pending post with id: {post_id}")
    return post_id


def get_pending_post(post_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored pending post.
    
    Args:
        post_id: Post identifier
        
    Returns:
        Post data or None if not found
    """
    return _pending_posts.get(post_id)


def remove_pending_post(post_id: str) -> bool:
    """
    Remove pending post from storage.
    
    Args:
        post_id: Post identifier
        
    Returns:
        True if removed, False if not found
    """
    if post_id in _pending_posts:
        del _pending_posts[post_id]
        logger.info(f"Removed pending post: {post_id}")
        return True
    return False


async def send_preview_to_admin(
    bot: Bot,
    admin_id: int,
    post_data: Dict[str, Any],
    reply_markup: InlineKeyboardMarkup
) -> bool:
    """
    Send post preview to admin with action buttons.
    
    Args:
        bot: Aiogram Bot instance
        admin_id: Admin user ID to send preview to
        post_data: Generated post data
        reply_markup: Inline keyboard with actions
        
    Returns:
        True if preview sent successfully
    """
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        preview_header = "📝 <b>Предпросмотр поста:</b>\n\n"
        full_text = preview_header + post_text
        
        # Truncate if too long for caption (max 1024 chars)
        if len(full_text) > 1024:
            full_text = full_text[:1020] + "..."
        
        if image_bytes:
            photo = BufferedInputFile(image_bytes, filename="preview.jpg")
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=full_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await bot.send_message(
                chat_id=admin_id,
                text=full_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        logger.info(f"Preview sent to admin {admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send preview: {e}", exc_info=True)
        return False


async def publish_pending_post(
    bot: Bot,
    post_id: str,
    channel_id: str
) -> bool:
    """
    Publish a pending post to channel.
    
    Args:
        bot: Aiogram Bot instance
        post_id: Stored post identifier
        channel_id: Target channel ID
        
    Returns:
        True if published successfully
    """
    post_data = get_pending_post(post_id)
    if not post_data:
        logger.error(f"Pending post not found: {post_id}")
        return False
    
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        if image_bytes:
            photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo,
                caption=post_text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=channel_id,
                text=post_text,
                parse_mode="HTML"
            )
        
        # Remove from pending after successful publish
        remove_pending_post(post_id)
        logger.info(f"Published pending post {post_id} to channel")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish pending post: {e}", exc_info=True)
        return False


async def post_to_channel(
    bot: Bot,
    channel_id: str,
    max_retries: int = 3,
    retry_delay: int = 300,
    preview_mode: bool = False,
    admin_id: Optional[int] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> Tuple[bool, Optional[str]]:
    """
    Generate and post content to the Telegram channel.
    
    Args:
        bot: Aiogram Bot instance
        channel_id: Target channel ID
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        preview_mode: If True, send preview to admin instead of publishing
        admin_id: Admin user ID for preview (required if preview_mode=True)
        reply_markup: Keyboard for preview message
    
    Returns:
        Tuple of (success: bool, post_id: Optional[str])
        post_id is returned only in preview_mode
    """
    # Generate post data
    post_data = await generate_post_data(max_retries=max_retries)
    
    if not post_data:
        return (False, None)
    
    # Preview mode: send to admin for review
    if preview_mode and admin_id:
        post_id = store_pending_post(post_data)
        
        # Import here to avoid circular imports
        from keyboards import preview_post_keyboard
        kb = reply_markup or preview_post_keyboard(post_id)
        
        success = await send_preview_to_admin(bot, admin_id, post_data, kb)
        return (success, post_id if success else None)
    
    # Direct mode: publish to channel immediately
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        if image_bytes:
            logger.info("Sending post with image to channel...")
            photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo,
                caption=post_text,
                parse_mode="HTML"
            )
        else:
            logger.warning("No image available, sending text-only post...")
            await bot.send_message(
                chat_id=channel_id,
                text=post_text,
                parse_mode="HTML"
            )
        
        logger.info("Post published successfully to channel")
        return (True, None)
        
    except Exception as e:
        logger.error(f"Failed to publish to channel: {e}", exc_info=True)
        return (False, None)


async def send_test_message(bot: Bot, channel_id: str) -> bool:
    """
    Send a test message to verify channel access.
    
    Args:
        bot: Aiogram Bot instance
        channel_id: Target channel ID
    
    Returns:
        True if message was sent, False otherwise
    """
    try:
        await bot.send_message(
            chat_id=channel_id,
            text="🔧 Тестовое сообщение от Utro Bot\n\nБот работает корректно!",
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logger.error(f"Test message failed: {e}")
        return False
