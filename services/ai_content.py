"""
AI Content Generation service using GPT-4o mini.
Generates unique post text, greetings, and PP recipes.
"""

import json
import logging
import asyncio
from datetime import date
from typing import Dict, List, Optional, Any

from openai import AsyncOpenAI

from config import config
from services.api_safety import safe_api_call, api_rate_limiter

logger = logging.getLogger(__name__)

# Initialize OpenAI async client
openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI async client."""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    return openai_client


# Day names in Russian
WEEKDAYS_RU = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье"
}

# Month names in Russian (genitive case)
MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}


SYSTEM_PROMPT = """You are a friendly Russian food blogger creating daily posts about CULINARY holidays (food-related only). Write in warm, conversational Russian with natural emoji usage.

CRITICAL REQUIREMENTS FOR PP (правильное питание) RECIPES:

🚫 SUGAR REPLACEMENT RULES (VERY IMPORTANT!):
- NEVER use regular sugar in recipes
- Stevia (стевия) is 200-300x sweeter than sugar! 
  → Use in DROPS: "3-5 капель стевии" = 1 tablespoon sugar
  → NEVER write "2 tablespoons stevia" - this is WRONG!
- Erythritol (эритрит): Use 1:1 ratio with sugar (same sweetness)
  → "2 ст.л. эритрита" = 2 tablespoons sugar equivalent
- Allulose (аллюлоза): Use 1.3:1 ratio 
  → "2.5 ст.л. аллюлозы" = 2 tablespoons sugar equivalent

EXAMPLE CORRECT SWEETENER USAGE:
❌ WRONG: "2 ст.л. стевии" (too sweet, would ruin dish!)
✅ RIGHT: "5-7 капель стевии" or "1/4 ч.л. стевии в порошке"
✅ RIGHT: "3 ст.л. эритрита" (erythritol is 1:1)

RECIPE REQUIREMENTS:
- Focus on PP (правильное питание) - healthy eating
- Use healthy ingredients: цельнозерновая мука, греческий йогурт, овсянка
- Create REALISTIC recipes that actually work
- Include exact measurements (grams, ml, teaspoons)
- Accurate cooking times
- Keep recipes simple (4-8 ingredients, 5-10 steps)
- Add helpful cooking tips

HOLIDAYS:
- Focus ONLY on FOOD/CULINARY holidays (День пиццы, День шоколада, etc.)
- Include 3 food holidays per post with brief descriptions
- Add emoji for each holiday

Output must be valid JSON with this EXACT structure:
{
  "greeting": "unique morning greeting text (1-2 sentences with emojis)",
  "holiday_text": "description of 3 FOOD holidays with emojis and brief fun facts",
  "recipe": {
    "name": "recipe name in Russian",
    "servings": number,
    "cooking_time": number in minutes,
    "calories_per_serving": number (approximate),
    "ingredients": ["ingredient 1 with exact amount", "ingredient 2 with amount", ...],
    "instructions": ["detailed step 1", "detailed step 2", ...],
    "tip": "helpful cooking tip in Russian",
    "image_prompt_en": "English description for image generation - describe the final dish appearance"
  }
}

IMPORTANT: Return ONLY valid JSON, no additional text before or after."""


def _format_date_russian(target_date: date) -> str:
    """Format date in Russian."""
    return f"{target_date.day} {MONTHS_RU[target_date.month]}"


def _get_weekday_russian(target_date: date) -> str:
    """Get weekday name in Russian."""
    return WEEKDAYS_RU[target_date.weekday()]


async def generate_post_content(
    target_date: date,
    holidays: List[Dict],
    quote: Dict,
    recipe_category: Optional[str] = None,
    custom_idea: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate complete post content using GPT-4o mini.
    
    Args:
        target_date: Date for the post
        holidays: List of holiday dictionaries from API
        quote: Quote dictionary with 'text' and 'author' keys
        recipe_category: Optional recipe category (pp, keto, vegan, etc.)
        custom_idea: Optional user's custom idea for the post
    
    Returns:
        Dictionary with greeting, holiday_text, and recipe
    """
    client = get_openai_client()
    
    # Format holidays list
    if holidays:
        holidays_list = "\n".join([
            f"- {h['name']}: {h.get('description', 'Праздник еды')[:100]}"
            for h in holidays[:5]  # Limit to 5 holidays
        ])
    else:
        holidays_list = "- Сегодня нет особых кулинарных праздников, но это не повод не приготовить что-то вкусное!"
    
    # Recipe type instruction based on category
    recipe_types = {
        "pp": "ПП (правильное питание) - низкокалорийный, сбалансированный",
        "keto": "Кето - высокожировой, без углеводов, максимум 5г углеводов",
        "vegan": "Веганский - без продуктов животного происхождения",
        "detox": "Детокс - легкий, очищающий, на овощах и зелени",
        "breakfast": "Полезный завтрак - энергичный старт дня",
        "dessert": "ПП-десерт - сладкий но полезный, без сахара",
        "smoothie": "Смузи - витаминный напиток из фруктов/овощей",
        "soup": "Полезный суп - сытный и согревающий"
    }
    
    recipe_instruction = recipe_types.get(recipe_category, "ПП (правильное питание)")
    
    # Check rate limits before making API call
    await api_rate_limiter.check_rate_limit("openai")
    
    # Add custom idea if provided
    custom_section = ""
    if custom_idea:
        custom_section = f"\n\nИДЕЯ АДМИНИСТРАТОРА (учти при создании поста):\n{custom_idea}\n"
    
    # Create user prompt
    user_prompt = f"""Создай пост для {_format_date_russian(target_date)} ({_get_weekday_russian(target_date)}).

Цитата дня: "{quote['text']}" — {quote['author']}

Праздники сегодня:
{holidays_list}

Тип рецепта: {recipe_instruction}{custom_section}

Создай уникальный пост с:
1. Оригинальным приветствием (1-2 предложения с эмодзи)
2. Описанием 3-х КУЛИНАРНЫХ праздников с краткими интересными фактами
3. Рецептом типа "{recipe_instruction}" по теме одного из праздников

⚠️ ВАЖНО по подсластителям:
- Стевия в 200-300 раз слаще сахара! Используй КАПЛИ (3-5 капель = 1 ст.л. сахара)
- Эритрит используй 1:1 как сахар
- НИКОГДА не пиши "2 ст.л. стевии" - это сделает блюдо несъедобным!

Рецепт должен быть:
- Реалистичным и проверенным
- С точными граммовками
- С калорийностью на порцию
- Простым (4-8 ингредиентов)
- С понятными шагами

Верни ТОЛЬКО валидный JSON!"""

    try:
        logger.info("Generating post content with GPT-4o mini...")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        logger.debug(f"GPT response: {content[:500]}...")
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate required fields
        required_fields = ["greeting", "holiday_text", "recipe"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        recipe = result["recipe"]
        recipe_fields = ["name", "servings", "cooking_time", "ingredients", "instructions", "tip", "image_prompt_en"]
        for field in recipe_fields:
            if field not in recipe:
                raise ValueError(f"Missing recipe field: {field}")
        
        logger.info(f"Generated content for recipe: {recipe['name']}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT response as JSON: {e}")
        return await _generate_fallback_content(target_date, holidays, quote)
    except Exception as e:
        logger.error(f"Error generating content: {e}", exc_info=True)
        return await _generate_fallback_content(target_date, holidays, quote)


async def _generate_fallback_content(
    target_date: date,
    holidays: List[Dict],
    quote: Dict
) -> Dict[str, Any]:
    """
    Generate fallback content when GPT fails.
    Uses a simpler approach or template.
    """
    logger.info("Using fallback content generation...")
    
    # Try a simpler GPT request
    client = get_openai_client()
    
    simple_prompt = f"""Создай простой ПП-рецепт на русском языке для {_format_date_russian(target_date)}.

Рецепт должен быть:
- Без сахара (используй эритрит или стевию)
- С 5-6 ингредиентами
- С 5 шагами приготовления
- Время приготовления 15-30 минут

Верни JSON:
{{"name": "название", "servings": 4, "cooking_time": 20, "ingredients": ["ингредиент 1", "ингредиент 2"], "instructions": ["шаг 1", "шаг 2"], "tip": "совет", "image_prompt_en": "dish description in english"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": simple_prompt}],
            max_tokens=1000,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        recipe = json.loads(response.choices[0].message.content)
        
        return {
            "greeting": f"Доброе утро, мои дорогие! ☀️ Пусть этот {_get_weekday_russian(target_date)} будет наполнен теплом и вкусной едой!",
            "holiday_text": f"Сегодня {_format_date_russian(target_date)} — отличный день для кулинарных экспериментов! 🍳✨",
            "recipe": recipe
        }
        
    except Exception as e:
        logger.error(f"Fallback generation also failed: {e}")
        # Ultimate fallback - static template
        return _get_static_fallback(target_date, quote)


def _get_static_fallback(target_date: date, quote: Dict) -> Dict[str, Any]:
    """Static fallback content when all else fails."""
    return {
        "greeting": f"Доброе утро, мои дорогие! ☀️ Пусть этот день будет вкусным и полезным!",
        "holiday_text": f"Сегодня {_format_date_russian(target_date)} — прекрасный день, чтобы приготовить что-то особенное! 🍽️",
        "recipe": {
            "name": "Овсяноблин с ягодами",
            "servings": 1,
            "cooking_time": 10,
            "ingredients": [
                "50г овсяных хлопьев",
                "1 яйцо",
                "50мл молока 1.5%",
                "50г свежих ягод",
                "1 ч.л. эритрита",
                "щепотка корицы"
            ],
            "instructions": [
                "Смешайте овсяные хлопья, яйцо и молоко в миске до однородности",
                "Добавьте эритрит и корицу, перемешайте",
                "Разогрейте антипригарную сковороду на среднем огне",
                "Вылейте тесто и распределите по сковороде",
                "Жарьте 2-3 минуты с каждой стороны до золотистого цвета",
                "Подавайте со свежими ягодами"
            ],
            "tip": "Для более нежной текстуры измельчите овсянку в блендере перед приготовлением",
            "image_prompt_en": "healthy oat pancake with fresh berries, breakfast, appetizing"
        }
    }


async def generate_greeting() -> str:
    """Generate a unique morning greeting."""
    client = get_openai_client()
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": "Напиши уникальное утреннее приветствие для кулинарного блога на русском языке. 1-2 предложения с эмодзи. Тёплое и дружелюбное."
            }],
            max_tokens=100,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating greeting: {e}")
        return "Доброе утро, мои дорогие! ☀️ Пусть этот день будет наполнен вкусной и полезной едой!"


async def generate_recipe(holiday_name: str) -> Dict[str, Any]:
    """
    Generate a PP recipe for a specific holiday.
    
    Args:
        holiday_name: Name of the holiday to create recipe for
    
    Returns:
        Recipe dictionary
    """
    client = get_openai_client()
    
    prompt = f"""Создай ПП-рецепт (правильное питание) для праздника "{holiday_name}".

ОБЯЗАТЕЛЬНО:
- БЕЗ САХАРА - используй эритрит, аллюлозу или стевию
- Здоровые ингредиенты: цельнозерновая мука, нежирные продукты
- 3-8 ингредиентов с точными граммовками
- 5-10 понятных шагов
- Реалистичный рецепт

Верни JSON:
{{"name": "название рецепта", "servings": число, "cooking_time": минуты, "ingredients": ["ингредиент с граммовкой"], "instructions": ["шаг"], "tip": "совет", "image_prompt_en": "описание блюда на английском"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        return _get_static_fallback(date.today(), {})["recipe"]
