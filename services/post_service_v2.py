"""
Post service v2 - main channel posting orchestration.
Coordinates holidays API, AI content generation, and channel posting.
Supports templates, channel links, image model selection.
"""

import json
import logging
import asyncio
import random
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InputMediaPhoto

from config import config
from services.settings_service import (
    get_settings, 
    get_channel_signature, 
    get_template_limit,
    should_split_post,
    TextTemplate,
    ImageModel,
    set_editing_state,
    clear_editing_state
)
from services.ai_content_v2 import (
    generate_post_content, 
    get_food_holidays_for_date,
    MONTHS_RU, 
    WEEKDAYS_RU
)

logger = logging.getLogger(__name__)

# Path to quotes file
QUOTES_FILE = Path(__file__).parent.parent / "data" / "quotes.json"

# Temporary storage for preview posts (post_id -> post_data)
_pending_posts: Dict[str, Dict[str, Any]] = {}

# Editing state storage (user_id -> original_text)
_editing_state: Dict[int, Dict[str, Any]] = {}

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
    content: Dict[str, Any],
    add_channel_link: bool = True
) -> str:
    """
    Format the full post text with HTML formatting.
    Respects template length limits.
    
    Args:
        target_date: Date of the post
        quote: Quote dictionary with 'text' and 'author'
        content: Generated content from AI
        add_channel_link: Whether to add channel signature
    
    Returns:
        Formatted HTML post text
    """
    settings = get_settings()
    max_length = get_template_limit()
    
    # Extract content parts
    greeting = content.get("greeting", "Доброе утро, мои дорогие! ☀️")
    holiday_text = content.get("holiday_text", "")
    recipe = content.get("recipe", {})
    
    # Format date
    date_str = f"{target_date.day} {MONTHS_RU[target_date.month]}"
    weekday = WEEKDAYS_RU[target_date.weekday()]
    
    # Format recipe
    recipe_name = recipe.get("name", "Полезное блюдо")
    servings = recipe.get("servings", 4)
    cooking_time = recipe.get("cooking_time", 30)
    calories = recipe.get("calories_per_serving", "")
    ingredients = recipe.get("ingredients", [])
    instructions = recipe.get("instructions", [])
    tip = recipe.get("tip", "")
    
    # Build ingredients list
    ingredients_text = "\n".join([f"• {ing}" for ing in ingredients])
    
    # Build instructions list
    instructions_text = "\n".join([
        f"{i}. {step}" for i, step in enumerate(instructions, 1)
    ])
    
    # Build full post based on template
    if settings.text_template == TextTemplate.SHORT.value:
        # Short template - compact version
        post_parts = [
            greeting,
            "",
            f"📅 <b>{date_str}</b>, {weekday}",
            "",
            holiday_text,
            "",
            f"🍳 <b>{recipe_name}</b>",
            f"⏱ {cooking_time} мин | 🍽 {servings} порций",
        ]
        if calories:
            post_parts.append(f"🔥 {calories} ккал/порция")
    
    elif settings.text_template == TextTemplate.CUSTOM.value and settings.custom_template:
        # Custom template
        try:
            post_text = settings.custom_template.format(
                greeting=greeting,
                date=date_str,
                weekday=weekday,
                quote_text=quote['text'],
                quote_author=quote['author'],
                holidays=holiday_text,
                recipe_name=recipe_name,
                servings=servings,
                cooking_time=cooking_time,
                calories=calories or "N/A",
                ingredients=ingredients_text,
                instructions=instructions_text,
                tip=tip
            )
            if add_channel_link:
                post_text += get_channel_signature(config.channel_id)
            return post_text[:max_length]
        except Exception as e:
            logger.warning(f"Custom template error: {e}, using default")
            # Fall through to default
    
    else:
        # Medium/Long template - full version
        post_parts = [
            greeting,
            "",
            f"<i>«{quote['text']}»</i> — {quote['author']}",
            "",
            f"📅 Сегодня <b>{date_str}</b>, {weekday}",
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
        # Find a good cut point
        post_text = post_text[:max_length - 3] + "..."
    
    return post_text


def _split_long_post(text: str, max_length: int = 4096) -> List[str]:
    """
    Split a long post into multiple messages.
    Tries to split at paragraph boundaries.
    
    Args:
        text: Full post text
        max_length: Maximum length per message
        
    Returns:
        List of message parts
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current = ""
    paragraphs = text.split("\n\n")
    
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_length:
            current += para + "\n\n"
        else:
            if current:
                parts.append(current.strip())
            current = para + "\n\n"
    
    if current:
        parts.append(current.strip())
    
    return parts


async def generate_image(recipe_name: str, image_prompt: str) -> Optional[bytes]:
    """
    Generate image using selected model (DALL-E 3 or Flux).
    
    Args:
        recipe_name: Recipe name for logging
        image_prompt: English prompt for image generation
        
    Returns:
        Image bytes or None
    """
    settings = get_settings()
    
    if not settings.image_enabled:
        logger.info("Image generation disabled in settings")
        return None
    
    if settings.image_model == ImageModel.FLUX.value:
        from services.flux_generator import generate_flux_image
        return await generate_flux_image(recipe_name, image_prompt)
    else:
        from services.image_generator import generate_food_image
        return await generate_food_image(recipe_name, image_prompt)


async def generate_post_data(
    max_retries: int = 3,
    force_image: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Generate post content and image without publishing.
    
    Args:
        max_retries: Maximum retry attempts
        force_image: Force image generation even if disabled
    
    Returns:
        Dictionary with post_text, image_bytes, content, quote, date
        or None if generation failed
    """
    settings = get_settings()
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating post data (attempt {attempt}/{max_retries})")
            start_time = datetime.now()
            
            # Step 1: Get current date
            today = date.today()
            logger.info(f"Generating post for {today}")
            
            # Step 2: Get food holidays (from local DB + API fallback)
            logger.info("Getting food holidays...")
            local_holidays = get_food_holidays_for_date(today)
            
            # Also try API if configured
            api_holidays = []
            try:
                from services.holidays_api import fetch_holidays_for_date
                api_holidays = await fetch_holidays_for_date(today)
            except Exception as e:
                logger.warning(f"API holidays fetch failed: {e}")
            
            holidays = local_holidays + api_holidays
            logger.info(f"Found {len(holidays)} food holidays")
            
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
            
            # Step 6: Generate image if enabled or forced
            image_bytes = None
            if settings.image_enabled or force_image:
                logger.info(f"Generating image with {settings.image_model}...")
                recipe = content.get("recipe", {})
                image_prompt = recipe.get("image_prompt_en", recipe.get("name", "healthy food"))
                image_bytes = await generate_image(recipe.get("name", "Recipe"), image_prompt)
            
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


def update_pending_post(post_id: str, new_text: str) -> bool:
    """
    Update text of a pending post.
    
    Args:
        post_id: Post identifier
        new_text: New post text
        
    Returns:
        True if updated, False if not found
    """
    if post_id in _pending_posts:
        _pending_posts[post_id]["post_text"] = new_text
        logger.info(f"Updated pending post text: {post_id}")
        return True
    return False


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


# Editing state management
def start_editing(user_id: int, post_id: str, message_id: int, original_text: str):
    """Start editing session for a post."""
    _editing_state[user_id] = {
        "post_id": post_id,
        "message_id": message_id,
        "original_text": original_text
    }
    set_editing_state(post_id, message_id)
    logger.info(f"Started editing for user {user_id}, post {post_id}")


def get_editing_state(user_id: int) -> Optional[Dict[str, Any]]:
    """Get editing state for user."""
    return _editing_state.get(user_id)


def cancel_editing(user_id: int) -> bool:
    """Cancel editing and restore original state."""
    if user_id in _editing_state:
        del _editing_state[user_id]
        clear_editing_state()
        logger.info(f"Cancelled editing for user {user_id}")
        return True
    return False


def finish_editing(user_id: int, new_text: str) -> Optional[str]:
    """
    Finish editing and update post text.
    
    Returns:
        post_id if successful, None otherwise
    """
    state = _editing_state.get(user_id)
    if not state:
        return None
    
    post_id = state["post_id"]
    if update_pending_post(post_id, new_text):
        del _editing_state[user_id]
        clear_editing_state()
        return post_id
    
    return None


async def send_preview_to_admin(
    bot: Bot,
    admin_id: int,
    post_data: Dict[str, Any],
    reply_markup: InlineKeyboardMarkup
) -> Optional[int]:
    """
    Send post preview to admin with action buttons.
    
    Args:
        bot: Aiogram Bot instance
        admin_id: Admin user ID to send preview to
        post_data: Generated post data
        reply_markup: Inline keyboard with actions
        
    Returns:
        Message ID if sent successfully, None otherwise
    """
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        preview_header = "📝 <b>Предпросмотр поста:</b>\n\n"
        full_text = preview_header + post_text
        
        # Handle caption length limit
        if image_bytes:
            if len(full_text) > 1024:
                # Send text separately if too long for caption
                truncated = full_text[:1020] + "..."
                photo = BufferedInputFile(image_bytes, filename="preview.jpg")
                msg = await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=truncated,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                photo = BufferedInputFile(image_bytes, filename="preview.jpg")
                msg = await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=full_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
        else:
            msg = await bot.send_message(
                chat_id=admin_id,
                text=full_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        logger.info(f"Preview sent to admin, msg_id: {msg.message_id}")
        return msg.message_id
        
    except Exception as e:
        logger.error(f"Failed to send preview: {e}", exc_info=True)
        return None


async def publish_pending_post(
    bot: Bot,
    post_id: str,
    channel_id: str
) -> bool:
    """
    Publish a pending post to channel.
    Handles long posts by splitting into multiple messages.
    
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
    
    settings = get_settings()
    
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        # Handle long posts
        if should_split_post() and len(post_text) > 1024:
            parts = _split_long_post(post_text)
            
            # First message with image
            if image_bytes and parts:
                photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
                first_text = parts[0][:1024] if len(parts[0]) > 1024 else parts[0]
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=first_text,
                    parse_mode="HTML"
                )
                parts = parts[1:]  # Remove first part
            
            # Send remaining parts as text
            for part in parts:
                await bot.send_message(
                    chat_id=channel_id,
                    text=part,
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.5)  # Avoid rate limits
        else:
            # Single message
            if image_bytes:
                caption = post_text[:1024] if len(post_text) > 1024 else post_text
                photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=caption,
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
        logger.info(f"Published post {post_id} to channel")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish pending post: {e}", exc_info=True)
        return False


async def post_to_channel(
    bot: Bot,
    channel_id: str,
    max_retries: int = 3,
    preview_mode: bool = False,
    admin_id: Optional[int] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    force_image: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Generate and post content to the Telegram channel.
    
    Args:
        bot: Aiogram Bot instance
        channel_id: Target channel ID
        max_retries: Maximum retry attempts
        preview_mode: If True, send preview to admin instead of publishing
        admin_id: Admin user ID for preview (required if preview_mode=True)
        reply_markup: Keyboard for preview message
        force_image: Force image generation (for autopost)
    
    Returns:
        Tuple of (success: bool, post_id: Optional[str])
        post_id is returned only in preview_mode
    """
    # Generate post data (force image for autopost)
    post_data = await generate_post_data(max_retries=max_retries, force_image=force_image)
    
    if not post_data:
        return (False, None)
    
    # Preview mode: send to admin for review
    if preview_mode and admin_id:
        post_id = store_pending_post(post_data)
        
        # Import here to avoid circular imports
        from keyboards_v2 import preview_post_keyboard
        kb = reply_markup or preview_post_keyboard(post_id)
        
        msg_id = await send_preview_to_admin(bot, admin_id, post_data, kb)
        return (msg_id is not None, post_id if msg_id else None)
    
    # Direct mode: publish to channel immediately
    settings = get_settings()
    
    try:
        post_text = post_data.get("post_text", "")
        image_bytes = post_data.get("image_bytes")
        
        # Handle long posts
        if should_split_post() and len(post_text) > 1024:
            parts = _split_long_post(post_text)
            
            if image_bytes and parts:
                photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=parts[0][:1024],
                    parse_mode="HTML"
                )
                for part in parts[1:]:
                    await bot.send_message(chat_id=channel_id, text=part, parse_mode="HTML")
                    await asyncio.sleep(0.5)
            else:
                for part in parts:
                    await bot.send_message(chat_id=channel_id, text=part, parse_mode="HTML")
                    await asyncio.sleep(0.5)
        else:
            if image_bytes:
                photo = BufferedInputFile(image_bytes, filename="recipe.jpg")
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=post_text[:1024],
                    parse_mode="HTML"
                )
            else:
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
