"""
Holidays API integration service.
Fetches real holidays from Calendarific API.
"""

import logging
import aiohttp
import asyncio
from datetime import date
from typing import List, Dict, Optional
from functools import lru_cache

from config import config
from services.api_safety import get_rate_limiter

logger = logging.getLogger(__name__)

# In-memory cache for daily holidays
_holidays_cache: Dict[str, List[Dict]] = {}

# Food-related keywords to filter holidays
FOOD_KEYWORDS = [
    "food", "eat", "cuisine", "dish", "meal", "breakfast", "lunch", "dinner",
    "chocolate", "coffee", "tea", "pizza", "burger", "cake", "pie", "cookie",
    "bread", "wine", "beer", "cocktail", "ice cream", "popcorn", "donut",
    "pancake", "waffle", "sandwich", "soup", "salad", "pasta", "rice",
    "fruit", "vegetable", "meat", "fish", "seafood", "cheese", "butter",
    "milk", "egg", "honey", "sugar", "salt", "pepper", "spice",
    "еда", "кухня", "блюдо", "завтрак", "обед", "ужин", "шоколад", "кофе",
    "чай", "пицца", "торт", "пирог", "печенье", "хлеб", "вино", "пиво",
    "мороженое", "попкорн", "пончик", "блин", "вафля", "суп", "салат",
    "паста", "рис", "фрукт", "овощ", "мясо", "рыба", "сыр", "масло",
    "молоко", "яйцо", "мёд", "день", "national", "international", "world"
]


def _get_cache_key(target_date: date) -> str:
    """Generate cache key for a date."""
    return target_date.strftime("%Y-%m-%d")


def _is_food_related(holiday: Dict) -> bool:
    """Check if holiday is food-related based on keywords."""
    name = holiday.get("name", "").lower()
    description = holiday.get("description", "").lower()
    combined = f"{name} {description}"
    
    return any(keyword.lower() in combined for keyword in FOOD_KEYWORDS)


async def _fetch_from_calendarific(
    target_date: date,
    country: str = "RU"
) -> List[Dict]:
    """
    Fetch holidays from Calendarific API.
    
    Args:
        target_date: Date to fetch holidays for
        country: Country code (RU for Russia)
    
    Returns:
        List of holiday dictionaries
    """
    if not config.holidays_api_key:
        logger.warning("Calendarific API key not configured")
        return []
    
    url = "https://calendarific.com/api/v2/holidays"
    params = {
        "api_key": config.holidays_api_key,
        "country": country,
        "year": target_date.year,
        "month": target_date.month,
        "day": target_date.day
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Calendarific API error: {response.status}")
                    return []
                
                data = await response.json()
                
                if data.get("meta", {}).get("code") != 200:
                    logger.error(f"Calendarific API returned error: {data}")
                    return []
                
                holidays_raw = data.get("response", {}).get("holidays", [])
                
                holidays = []
                for h in holidays_raw:
                    holidays.append({
                        "name": h.get("name", ""),
                        "description": h.get("description", ""),
                        "type": ", ".join(h.get("type", ["observance"])),
                        "country": country,
                        "primary_type": h.get("primary_type", "observance")
                    })
                
                logger.info(f"Fetched {len(holidays)} holidays from Calendarific for {country}")
                return holidays
                
    except asyncio.TimeoutError:
        logger.error("Calendarific API timeout")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"Calendarific API connection error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching from Calendarific: {e}", exc_info=True)
        return []


async def fetch_holidays_for_date(target_date: date) -> List[Dict]:
    """
    Fetch holidays for a specific date with caching.
    
    Combines Russian holidays and international food-related holidays.
    Uses in-memory cache to avoid repeated API calls.
    
    Args:
        target_date: Date to fetch holidays for
    
    Returns:
        List of holiday dictionaries with name, description, type
    """
    cache_key = _get_cache_key(target_date)
    
    # Check cache first
    if cache_key in _holidays_cache:
        logger.debug(f"Returning cached holidays for {target_date}")
        return _holidays_cache[cache_key]
    
    all_holidays = []
    
    try:
        # Check rate limits before making API call
        await get_rate_limiter("calendarific").check_rate_limit()
        
        # Fetch Russian holidays
        ru_holidays = await _fetch_from_calendarific(target_date, "RU")
        all_holidays.extend(ru_holidays)
        
        # Fetch international holidays (US has many food holidays)
        await asyncio.sleep(0.5)  # Rate limiting
        us_holidays = await _fetch_from_calendarific(target_date, "US")
        
        # Filter US holidays for food-related only
        food_holidays = [h for h in us_holidays if _is_food_related(h)]
        all_holidays.extend(food_holidays)
        
        # Remove duplicates by name
        seen_names = set()
        unique_holidays = []
        for h in all_holidays:
            name_lower = h["name"].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_holidays.append(h)
        
        # Sort: food-related first, then by name
        unique_holidays.sort(key=lambda x: (not _is_food_related(x), x["name"]))
        
        # Cache the results
        _holidays_cache[cache_key] = unique_holidays
        
        # Clean old cache entries (keep only today)
        keys_to_remove = [k for k in _holidays_cache if k != cache_key]
        for k in keys_to_remove:
            del _holidays_cache[k]
        
        logger.info(f"Total holidays for {target_date}: {len(unique_holidays)}")
        return unique_holidays
        
    except Exception as e:
        logger.error(f"Error fetching holidays: {e}", exc_info=True)
        return []


async def get_international_food_holidays(target_date: date) -> List[Dict]:
    """
    Fetch specifically international food-related holidays.
    
    Args:
        target_date: Date to fetch holidays for
    
    Returns:
        List of food-related holiday dictionaries
    """
    try:
        # Fetch from multiple countries for more food holidays
        countries = ["US", "GB", "CA", "AU"]
        all_food_holidays = []
        
        for country in countries:
            holidays = await _fetch_from_calendarific(target_date, country)
            food_holidays = [h for h in holidays if _is_food_related(h)]
            all_food_holidays.extend(food_holidays)
            await asyncio.sleep(0.3)  # Rate limiting
        
        # Remove duplicates
        seen_names = set()
        unique_holidays = []
        for h in all_food_holidays:
            name_lower = h["name"].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_holidays.append(h)
        
        return unique_holidays
        
    except Exception as e:
        logger.error(f"Error fetching international food holidays: {e}", exc_info=True)
        return []


def clear_cache() -> None:
    """Clear the holidays cache."""
    global _holidays_cache
    _holidays_cache = {}
    logger.info("Holidays cache cleared")


async def test_holidays(test_date: date = None) -> Dict:
    """
    Test holidays function - returns detailed diagnostic info.
    
    Args:
        test_date: Date to test (defaults to today)
    
    Returns:
        Dict with detailed test results
    """
    if test_date is None:
        test_date = date.today()
    
    result = {
        "date": test_date.isoformat(),
        "date_formatted": test_date.strftime("%d.%m.%Y"),
        "cache_key": _get_cache_key(test_date),
        "api_key_configured": bool(config.holidays_api_key),
        "ru_holidays": [],
        "us_holidays": [],
        "food_holidays": [],
        "all_holidays": [],
        "errors": [],
        "status": "success"
    }
    
    try:
        # Fetch Russian holidays
        logger.info(f"Testing holidays for {test_date}...")
        ru_holidays = await _fetch_from_calendarific(test_date, "RU")
        result["ru_holidays"] = [h["name"] for h in ru_holidays]
        result["ru_count"] = len(ru_holidays)
    except Exception as e:
        result["errors"].append(f"RU fetch error: {str(e)}")
    
    try:
        # Fetch US holidays
        await asyncio.sleep(0.3)
        us_holidays = await _fetch_from_calendarific(test_date, "US")
        result["us_holidays"] = [h["name"] for h in us_holidays]
        result["us_count"] = len(us_holidays)
        
        # Filter food-related
        food_holidays = [h for h in us_holidays if _is_food_related(h)]
        result["food_holidays"] = [h["name"] for h in food_holidays]
        result["food_count"] = len(food_holidays)
    except Exception as e:
        result["errors"].append(f"US fetch error: {str(e)}")
    
    try:
        # Get combined result
        all_holidays = await fetch_holidays_for_date(test_date)
        result["all_holidays"] = [h["name"] for h in all_holidays]
        result["total_count"] = len(all_holidays)
    except Exception as e:
        result["errors"].append(f"Combined fetch error: {str(e)}")
    
    # Determine status
    if result["errors"]:
        result["status"] = "error"
        result["message"] = "Произошли ошибки при получении праздников"
    elif not result["all_holidays"]:
        result["status"] = "no_holidays"
        result["message"] = f"На {result['date_formatted']} праздников не найдено"
    else:
        result["status"] = "success"
        result["message"] = f"Найдено {len(result['all_holidays'])} праздников на {result['date_formatted']}"
    
    logger.info(f"Test result: {result['message']}")
    return result
