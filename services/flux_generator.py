"""
Flux Image Generation service.
Alternative to DALL-E 3 using Together AI's Flux model.
"""

import logging
import asyncio
import aiohttp
import base64
from typing import Optional

from config import config
from services.settings_service import get_settings

logger = logging.getLogger(__name__)


async def generate_flux_image(
    recipe_name: str,
    english_prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Generate a food image using Flux model via Together AI.
    
    Args:
        recipe_name: Name of the recipe (for logging)
        english_prompt: English description of the dish
        max_retries: Maximum retry attempts
    
    Returns:
        Image bytes or None if generation fails
    """
    settings = get_settings()
    
    if not settings.flux_api_key:
        logger.error("Flux API key not configured")
        return None
    
    # Enhanced prompt for food photography
    enhanced_prompt = (
        f"Professional food photography of {english_prompt}, "
        "healthy meal, appetizing presentation, natural lighting, "
        "on a beautiful white ceramic plate, rustic wooden table background, "
        "garnished elegantly, high resolution, food blog style, "
        "warm and inviting atmosphere, no text or watermarks, photorealistic"
    )
    
    headers = {
        "Authorization": f"Bearer {settings.flux_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",  # Free tier
        "prompt": enhanced_prompt,
        "width": 1024,
        "height": 1024,
        "steps": 4,
        "n": 1,
        "response_format": "b64_json"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating Flux image for '{recipe_name}' (attempt {attempt}/{max_retries})")
            
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    settings.flux_api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract base64 image
                        if "data" in data and len(data["data"]) > 0:
                            b64_image = data["data"][0].get("b64_json")
                            if b64_image:
                                image_bytes = base64.b64decode(b64_image)
                                logger.info(f"Flux image generated successfully ({len(image_bytes)} bytes)")
                                return image_bytes
                        
                        logger.warning(f"Unexpected Flux response format: {data}")
                        
                    elif response.status == 429:
                        logger.warning("Flux rate limit hit, waiting...")
                        await asyncio.sleep(5 * attempt)
                        
                    else:
                        error_text = await response.text()
                        logger.error(f"Flux API error {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            logger.error(f"Flux image generation timeout (attempt {attempt})")
        except aiohttp.ClientError as e:
            logger.error(f"Flux connection error: {e}")
        except Exception as e:
            logger.error(f"Flux generation error: {e}", exc_info=True)
        
        if attempt < max_retries:
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
    
    logger.error(f"Failed to generate Flux image after {max_retries} attempts")
    return None


async def generate_flux_pro_image(
    recipe_name: str,
    english_prompt: str,
    max_retries: int = 3
) -> Optional[bytes]:
    """
    Generate a food image using Flux Pro model (higher quality, paid).
    
    Args:
        recipe_name: Name of the recipe (for logging)
        english_prompt: English description of the dish
        max_retries: Maximum retry attempts
    
    Returns:
        Image bytes or None if generation fails
    """
    settings = get_settings()
    
    if not settings.flux_api_key:
        logger.error("Flux API key not configured")
        return None
    
    # Enhanced prompt for food photography
    enhanced_prompt = (
        f"Professional food photography of {english_prompt}, "
        "healthy meal, appetizing presentation, natural lighting, "
        "on a beautiful white ceramic plate, rustic wooden table background, "
        "garnished elegantly, high resolution, food blog style, "
        "warm and inviting atmosphere, no text or watermarks, photorealistic, 8k"
    )
    
    headers = {
        "Authorization": f"Bearer {settings.flux_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "black-forest-labs/FLUX.1.1-pro",  # Pro tier
        "prompt": enhanced_prompt,
        "width": 1024,
        "height": 1024,
        "steps": 28,
        "n": 1,
        "response_format": "b64_json"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating Flux Pro image for '{recipe_name}' (attempt {attempt}/{max_retries})")
            
            timeout = aiohttp.ClientTimeout(total=180)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    settings.flux_api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "data" in data and len(data["data"]) > 0:
                            b64_image = data["data"][0].get("b64_json")
                            if b64_image:
                                image_bytes = base64.b64decode(b64_image)
                                logger.info(f"Flux Pro image generated ({len(image_bytes)} bytes)")
                                return image_bytes
                        
                    else:
                        error_text = await response.text()
                        logger.error(f"Flux Pro API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Flux Pro generation error: {e}", exc_info=True)
        
        if attempt < max_retries:
            await asyncio.sleep(2 ** attempt)
    
    return None
