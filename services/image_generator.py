"""
Image Generation service.
Supports DALL-E 3 (OpenAI) and Flux (Together AI) models.
Generates food photography images for recipes.
"""

import logging
import asyncio
import aiohttp
from typing import Optional

from openai import AsyncOpenAI

from config import config
from services.api_safety import get_rate_limiter
from services.settings_service import get_settings, ImageModel

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI async client."""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    return openai_client


async def generate_image(
    prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Generate an image using the currently selected model (DALL-E 3 or Flux).
    
    Args:
        prompt: Description of the image to generate
        max_retries: Maximum number of retry attempts
    
    Returns:
        Image bytes or None if generation fails
    """
    settings = get_settings()
    
    # Check which model is selected
    if settings.image_model == ImageModel.DALLE3.value:
        logger.info(f"Using DALL-E 3 for image generation")
        return await generate_dalle_image(prompt, max_retries)
    else:
        logger.info(f"Using Flux for image generation")
        return await generate_flux_image(prompt, max_retries)


async def generate_dalle_image(
    prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """Generate image using DALL-E 3."""
    client = get_openai_client()
    
    # Enhance prompt for better food photography
    enhanced_prompt = (
        f"Professional food photography of {prompt}, "
        "healthy meal, appetizing presentation, natural lighting, "
        "on a beautiful white ceramic plate, rustic wooden table background, "
        "garnished elegantly, high resolution, food blog style, "
        "warm and inviting atmosphere, no text or watermarks"
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            await get_rate_limiter("dalle").check_rate_limit()
            
            logger.info(f"Generating DALL-E image (attempt {attempt}/{max_retries})")
            
            response = await client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            logger.info(f"DALL-E image generated, downloading...")
            
            image_bytes = await _download_image(image_url)
            
            if image_bytes:
                logger.info(f"DALL-E image downloaded ({len(image_bytes)} bytes)")
                return image_bytes
            else:
                logger.warning(f"Failed to download DALL-E image on attempt {attempt}")
                
        except Exception as e:
            logger.error(f"DALL-E error (attempt {attempt}): {e}", exc_info=True)
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
    
    logger.error(f"DALL-E failed after {max_retries} attempts")
    return None


async def generate_flux_image(
    prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """Generate image using Flux model via Together AI."""
    settings = get_settings()
    
    if not settings.flux_api_key:
        logger.error("Flux API key not configured")
        return None
    
    enhanced_prompt = (
        f"Professional food photography: {prompt}, "
        "appetizing, well-plated, natural lighting, high quality"
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            await get_rate_limiter("flux").check_rate_limit()
            
            logger.info(f"Generating Flux image (attempt {attempt}/{max_retries})")
            
            headers = {
                "Authorization": f"Bearer {settings.flux_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": enhanced_prompt,
                "width": 1024,
                "height": 1024,
                "steps": 4,
                "n": 1,
                "response_format": "b64_json"
            }
            
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    settings.flux_api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data") and len(data["data"]) > 0:
                            import base64
                            b64_image = data["data"][0].get("b64_json")
                            if b64_image:
                                image_bytes = base64.b64decode(b64_image)
                                logger.info(f"Flux image generated ({len(image_bytes)} bytes)")
                                return image_bytes
                    else:
                        error_text = await response.text()
                        logger.error(f"Flux API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Flux error (attempt {attempt}): {e}", exc_info=True)
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
    
    logger.error(f"Flux failed after {max_retries} attempts")
    return None


async def generate_food_image(
    recipe_name: str,
    english_prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Generate a food image for a recipe using selected model.
    
    Args:
        recipe_name: Name of the recipe (for logging)
        english_prompt: English description of the dish
        max_retries: Maximum number of retry attempts
    
    Returns:
        Image bytes or None if generation fails
    """
    logger.info(f"Generating image for recipe: {recipe_name}")
    return await generate_image(english_prompt, max_retries)


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
