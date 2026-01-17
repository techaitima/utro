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
from utils.logger import mask_user_id, mask_channel_id

logger = logging.getLogger(__name__)

# Path to quotes file
QUOTES_FILE = Path(__file__).parent.parent / "data" / "quotes.json"

# Temporary storage for preview posts (post_id -> post_data)
_pending_posts: Dict[str, Dict[str, Any]] = {}

# Multi-post configuration
MULTIPOST_THRESHOLD = 1000  # Characters threshold for splitting
MULTIPOST_TARGET_LENGTH = 850  # Target length per part

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


def split_post_into_parts(text: str, max_length: int = MULTIPOST_TARGET_LENGTH) -> list[str]:
    """
    Split long post text into multiple parts.
    
    Splits by paragraphs first, then by sentences if needed.
    Each part gets a number suffix like "(1/3)".
    
    Args:
        text: Full post text
        max_length: Maximum length per part
        
    Returns:
        List of text parts with numbering
    """
    if len(text) <= MULTIPOST_THRESHOLD:
        return [text]
    
    # Split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")
    
    parts = []
    current_part = ""
    
    for para in paragraphs:
        # Check if adding this paragraph exceeds limit
        test_text = current_part + ("\n\n" if current_part else "") + para
        
        if len(test_text) <= max_length:
            current_part = test_text
        else:
            # Current part is full, save it
            if current_part:
                parts.append(current_part)
            
            # Start new part
            if len(para) <= max_length:
                current_part = para
            else:
                # Paragraph is too long, split by sentences
                sentences = split_by_sentences(para)
                for sent in sentences:
                    if len(current_part) + len(sent) + 2 <= max_length:
                        current_part += (" " if current_part else "") + sent
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = sent
    
    # Don't forget the last part
    if current_part:
        parts.append(current_part)
    
    # Add numbering to each part
    total = len(parts)
    if total > 1:
        numbered_parts = []
        for i, part in enumerate(parts, 1):
            numbered_parts.append(f"{part}\n\n<i>({i}/{total})</i>")
        return numbered_parts
    
    return parts


def split_by_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    import re
    # Split on . ! ? followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sentences if s.strip()]


def format_post_text(
    target_date: date,
    quote: Dict[str, str],
    content: Dict[str, Any],
    add_channel_link: bool = True
) -> str:
    """
    Format the full post text with HTML formatting.
    
    Args:
        target_date: Date of the post
        quote: Quote dictionary with 'text' and 'author'
        content: Generated content from AI
        add_channel_link: Whether to add channel signature at the end
    
    Returns:
        Formatted HTML post text
    """
    from services.settings_service import get_settings, get_channel_signature, get_template_limit, TextTemplate
    
    settings = get_settings()
    max_length = get_template_limit()
    
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
    
    # Get calories if available
    calories = recipe.get("calories_per_serving", "")
    
    # Build full post based on template
    if settings.text_template == TextTemplate.SHORT.value:
        # Short template - compact version
        post_parts = [
            greeting,
            "",
            f"📅 <b>{date_str}</b>, {WEEKDAYS_RU[target_date.weekday()]}",
            "",
            holiday_text,
            "",
            f"🍳 <b>{recipe_name}</b>",
            f"⏱ {cooking_time} мин | 🍽 {servings} порций",
        ]
        if calories:
            post_parts.append(f"🔥 {calories} ккал/порция")
    else:
        # Medium/Long template - full version
        post_parts = [
            greeting,
            "",
            f"<i>«{quote['text']}»</i> — {quote['author']}",
            "",
            f"📅 Сегодня <b>{date_str}</b>, {WEEKDAYS_RU[target_date.weekday()]}",
            "",
            holiday_text,
            "",
            f"📖 <b>Рецепт: {recipe_name}</b>",
            "",
            f"🍽 Порции: {servings} | ⏱ Время: {cooking_time} мин",
        ]
        
        if calories:
            post_parts[-1] += f" | 🔥 {calories} ккал"
        
        post_parts.extend([
            "",
            "<b>Ингредиенты:</b>",
            ingredients_text,
            "",
            "<b>Приготовление:</b>",
            instructions_text,
        ])
        
        # Add tip if present
        if tip:
            post_parts.extend(["", f"💡 <b>Совет:</b> {tip}"])
    
    post_text = "\n".join(post_parts)
    
    # Add channel signature
    if add_channel_link:
        post_text += get_channel_signature(config.channel_id)
    
    # Truncate if needed (for SHORT and MEDIUM templates)
    if len(post_text) > max_length and settings.text_template != TextTemplate.LONG.value:
        post_text = post_text[:max_length - 3] + "..."
    
    return post_text


async def generate_post_data(
    max_retries: int = 3,
    recipe_category: Optional[str] = None,
    custom_idea: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Generate post content and image without publishing.
    
    Args:
        max_retries: Maximum retry attempts
        recipe_category: Optional recipe category (pp, keto, vegan, etc.)
        custom_idea: Optional user's custom idea for post content
    
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
            
            # Step 4: Generate AI content (with optional recipe category and custom idea)
            logger.info("Generating AI content...")
            content = await generate_post_content(
                today, holidays, quote, 
                recipe_category=recipe_category,
                custom_idea=custom_idea
            )
            logger.info(f"Generated recipe: {content['recipe']['name']}")
            
            # Step 5: Format post text
            post_text = format_post_text(today, quote, content)
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
    Handles multi-part posts.
    
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
        
        # Check if we need to split the post
        parts = split_post_into_parts(post_text)
        is_multipost = len(parts) > 1
        
        # Store parts info in post_data
        if is_multipost:
            post_data["parts"] = parts
            post_data["is_multipost"] = True
            post_data["total_parts"] = len(parts)
        
        preview_header = "📝 <b>Предпросмотр поста:</b>\n\n"
        
        if is_multipost:
            # Send each part as separate message
            for i, part in enumerate(parts):
                is_first = i == 0
                is_last = i == len(parts) - 1
                
                part_text = preview_header + part if is_first else part
                
                # Only send image with first part
                if is_first and image_bytes:
                    # Truncate if too long for caption
                    if len(part_text) > 1024:
                        part_text = part_text[:1020] + "..."
                    
                    photo = BufferedInputFile(image_bytes, filename="preview.jpg")
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=photo,
                        caption=part_text,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=part_text,
                        parse_mode="HTML",
                        reply_markup=reply_markup if is_last else None
                    )
                
                # Small delay between parts
                if not is_last:
                    await asyncio.sleep(0.5)
            
            logger.info(f"Multi-part preview ({len(parts)} parts) sent to admin")
        else:
            # Single post - original logic
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
        
        logger.info(f"Preview sent to admin {mask_user_id(admin_id, config.debug_mode)}")
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
    Handles multi-part posts with delays.
    
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
        image_bytes = post_data.get("image_bytes")
        is_multipost = post_data.get("is_multipost", False)
        parts = post_data.get("parts", [])
        
        if is_multipost and parts:
            # Publish multi-part post
            for i, part in enumerate(parts):
                is_first = i == 0
                is_last = i == len(parts) - 1
                
                if is_first and image_bytes:
                    # First part with image
                    if len(part) > 1024:
                        part = part[:1020] + "..."
                    photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=photo,
                        caption=part,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        chat_id=channel_id,
                        text=part,
                        parse_mode="HTML"
                    )
                
                # Delay between parts (except after last)
                if not is_last:
                    await asyncio.sleep(1.5)
            
            logger.info(f"Published multi-part post ({len(parts)} parts) to channel")
        else:
            # Single post
            post_text = post_data.get("post_text", "")
            
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
        logger.info(f"Published pending post {post_id} to channel {mask_channel_id(channel_id, config.debug_mode)}")
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
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    recipe_category: Optional[str] = None,
    custom_idea: Optional[str] = None
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
        recipe_category: Optional recipe category (pp, keto, vegan, etc.)
        custom_idea: Optional user's custom idea for post
    
    Returns:
        Tuple of (success: bool, post_id: Optional[str])
        post_id is returned only in preview_mode
    """
    # Generate post data
    post_data = await generate_post_data(
        max_retries=max_retries, 
        recipe_category=recipe_category,
        custom_idea=custom_idea
    )
    
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
