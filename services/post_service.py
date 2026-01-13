"""
Post service - main channel posting orchestration.
Coordinates holidays API, AI content generation, and channel posting.
"""

import json
import logging
import asyncio
import random
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import config
from services.holidays_api import fetch_holidays_for_date
from services.ai_content import generate_post_content, MONTHS_RU, WEEKDAYS_RU
from services.image_generator import generate_food_image

logger = logging.getLogger(__name__)

# Path to quotes file
QUOTES_FILE = Path(__file__).parent.parent / "data" / "quotes.json"

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


async def post_to_channel(
    bot: Bot,
    channel_id: str,
    max_retries: int = 3,
    retry_delay: int = 300
) -> bool:
    """
    Generate and post content to the Telegram channel.
    
    Args:
        bot: Aiogram Bot instance
        channel_id: Target channel ID
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        True if post was successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Starting post generation (attempt {attempt}/{max_retries})")
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
            
            # Step 7: Send to channel
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
                # Fallback: send text only
                logger.warning("No image available, sending text-only post...")
                await bot.send_message(
                    chat_id=channel_id,
                    text=post_text,
                    parse_mode="HTML"
                )
            
            # Calculate and log execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Post published successfully in {execution_time:.1f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Post attempt {attempt} failed: {e}", exc_info=True)
            
            if attempt < max_retries:
                logger.info(f"Waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed")
    
    return False


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
