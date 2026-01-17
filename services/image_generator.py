"""
DALL-E 3 Image Generation service.
Generates food photography images for recipes.
"""

import logging
import asyncio
import aiohttp
from typing import Optional

from openai import AsyncOpenAI

from config import config
from services.api_safety import get_rate_limiter

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI async client."""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    return openai_client


async def generate_food_image(
    recipe_name: str,
    english_prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Generate a food image using DALL-E 3.
    
    Args:
        recipe_name: Name of the recipe (for logging)
        english_prompt: English description of the dish for image generation
        max_retries: Maximum number of retry attempts
    
    Returns:
        Image bytes or None if generation fails
    """
    client = get_openai_client()
    
    # Enhance prompt for better food photography
    enhanced_prompt = (
        f"Professional food photography of {english_prompt}, "
        "healthy meal, appetizing presentation, natural lighting, "
        "on a beautiful white ceramic plate, rustic wooden table background, "
        "garnished elegantly, high resolution, food blog style, "
        "warm and inviting atmosphere, no text or watermarks"
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            # Check rate limits before making API call
            await get_rate_limiter("dalle").check_rate_limit()
            
            logger.info(f"Generating image for '{recipe_name}' (attempt {attempt}/{max_retries})"))
            
            # Generate image with DALL-E 3
            response = await client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            # Get image URL
            image_url = response.data[0].url
            logger.info(f"Image generated, downloading from URL...")
            
            # Download image
            image_bytes = await _download_image(image_url)
            
            if image_bytes:
                logger.info(f"Image downloaded successfully ({len(image_bytes)} bytes)")
                return image_bytes
            else:
                logger.warning(f"Failed to download image on attempt {attempt}")
                
        except Exception as e:
            logger.error(f"Image generation error (attempt {attempt}): {e}", exc_info=True)
            
            if attempt < max_retries:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
    
    logger.error(f"Failed to generate image after {max_retries} attempts")
    return None


async def _download_image(
    url: str,
    timeout: int = 30
) -> Optional[bytes]:
    """
    Download image from URL.
    
    Args:
        url: Image URL
        timeout: Request timeout in seconds
    
    Returns:
        Image bytes or None if download fails
    """
    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Image download failed with status {response.status}")
                    return None
                    
    except asyncio.TimeoutError:
        logger.error("Image download timeout")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Image download error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {e}", exc_info=True)
        return None


async def generate_simple_food_image(dish_description: str) -> Optional[bytes]:
    """
    Generate a simple food image with minimal prompt.
    Fallback method when detailed prompt fails.
    
    Args:
        dish_description: Simple description of the dish
    
    Returns:
        Image bytes or None if generation fails
    """
    client = get_openai_client()
    
    simple_prompt = f"Appetizing {dish_description}, food photography, white background"
    
    try:
        logger.info(f"Generating simple image for: {dish_description}")
        
        response = await client.images.generate(
            model="dall-e-3",
            prompt=simple_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        image_url = response.data[0].url
        return await _download_image(image_url)
        
    except Exception as e:
        logger.error(f"Simple image generation failed: {e}")
        return None
