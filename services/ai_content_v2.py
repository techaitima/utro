"""
AI Content Generation service using GPT-4o mini.
Generates unique post text, greetings, and PP/Keto recipes.
Focuses on food holidays and healthy recipes.
"""

import json
import logging
import asyncio
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Any

from openai import AsyncOpenAI

from config import config
from services.settings_service import get_settings, RecipeType

logger = logging.getLogger(__name__)

# Initialize OpenAI async client
openai_client: Optional[AsyncOpenAI] = None

# Path to food holidays file
FOOD_HOLIDAYS_FILE = Path(__file__).parent.parent / "data" / "food_holidays.json"


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

# Month names for file keys
MONTH_KEYS = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december"
}


def _load_food_holidays() -> Dict[str, List[Dict]]:
    """Load food holidays from JSON file."""
    try:
        with open(FOOD_HOLIDAYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Food holidays file not found: {FOOD_HOLIDAYS_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing food holidays file: {e}")
        return {}


def get_food_holidays_for_date(target_date: date) -> List[Dict]:
    """
    Get food holidays for a specific date from local database.
    
    Args:
        target_date: Date to get holidays for
        
    Returns:
        List of holiday dictionaries with name, emoji
    """
    holidays_data = _load_food_holidays()
    month_key = MONTH_KEYS.get(target_date.month)
    
    if not month_key or month_key not in holidays_data:
        return []
    
    month_holidays = holidays_data[month_key]
    day_holidays = [h for h in month_holidays if h.get("day") == target_date.day]
    
    return day_holidays


def _get_sweetener_prompt(recipe_type: str) -> str:
    """Get sweetener instructions based on recipe type."""
    if recipe_type == RecipeType.KETO.value:
        return """
КРИТИЧЕСКИ ВАЖНО про ПОДСЛАСТИТЕЛИ (для КЕТО):
- Используй ТОЛЬКО: эритрит ИЛИ аллюлозу
- Эритрит: используй как сахар 1:1 (например, 50г эритрита = 50г сахара)
- Аллюлоза: используй 1.3:1 (65г аллюлозы = 50г сахара)
- НИКОГДА не используй стевию для кето-рецептов
- БЕЗ обычного сахара, мёда, фруктозы
- Считай чистые углеводы (общие углеводы - клетчатка - сахароспирты)
"""
    else:  # PP or MIXED
        return """
КРИТИЧЕСКИ ВАЖНО про ПОДСЛАСТИТЕЛИ (для ПП):
- Основные: эритрит ИЛИ аллюлоза (измеряй в граммах/столовых ложках)
- Эритрит: 1:1 как сахар (30г эритрита заменяет 30г сахара)
- Аллюлоза: 1.3:1 (39г аллюлозы заменяет 30г сахара)
- СТЕВИЯ: ТОЛЬКО в каплях! Стевия в 200-300 раз слаще сахара!
  * 2-3 капли стевии = 1 чайная ложка сахара
  * 5-7 капель стевии = 1 столовая ложка сахара
  * НИКОГДА не пиши "2 столовые ложки стевии" - это ОШИБКА!
- Если используешь стевию, пиши: "3-5 капель стевии (по вкусу)"
- БЕЗ обычного сахара
"""


def _get_recipe_type_prompt(recipe_type: str) -> str:
    """Get recipe requirements based on type."""
    if recipe_type == RecipeType.KETO.value:
        return """
Тип рецепта: КЕТО (кетогенная диета)
Требования:
- Максимум 5-10г чистых углеводов на порцию
- Высокое содержание жиров (70-80% калорий)
- Умеренный белок
- БЕЗ: сахара, муки, крахмала, картофеля, риса, бобовых
- МОЖНО: авокадо, орехи, сыр, сливки, масло, яйца, мясо, рыба, некрахмалистые овощи
- Используй миндальную или кокосовую муку вместо обычной
"""
    else:  # PP
        return """
Тип рецепта: ПП (правильное питание)
Требования:
- Сбалансированное соотношение БЖУ
- Умеренные калории
- Цельнозерновые продукты вместо рафинированных
- Нежирные белки
- Много овощей и зелени
- МОЖНО: цельнозерновая мука, овсянка, гречка, киноа, нежирное мясо/рыба
- Минимум обработанных продуктов
"""


SYSTEM_PROMPT_TEMPLATE = """Ты дружелюбный русский фуд-блогер, создающий ежедневные посты о кулинарных праздниках. Пиши тепло, по-дружески на русском языке с естественным использованием эмодзи.

{sweetener_prompt}

{recipe_type_prompt}

ТРЕБОВАНИЯ К КОНТЕНТУ:
- Создавай РЕАЛИСТИЧНЫЕ рецепты, которые реально работают на кухне
- Указывай ТОЧНЫЕ граммовки и объёмы
- Точное время приготовления
- Простые рецепты (3-8 ингредиентов, 5-10 шагов)
- Добавляй полезные кулинарные советы
- Используй эмодзи естественно

Ответ ТОЛЬКО в формате JSON со структурой:
{{
  "greeting": "уникальное утреннее приветствие (1-2 предложения с эмодзи)",
  "holidays": [
    {{"name": "название праздника 1", "emoji": "🍎", "description": "краткое описание (1 предложение)"}},
    {{"name": "название праздника 2", "emoji": "🍕", "description": "краткое описание (1 предложение)"}},
    {{"name": "название праздника 3", "emoji": "🍫", "description": "краткое описание (1 предложение)"}}
  ],
  "recipe": {{
    "name": "название рецепта на русском",
    "servings": число_порций,
    "cooking_time": время_в_минутах,
    "calories_per_serving": калории_на_порцию,
    "ingredients": ["ингредиент 1 с точной граммовкой", "ингредиент 2 с граммовкой", ...],
    "instructions": ["подробный шаг 1", "подробный шаг 2", ...],
    "tip": "полезный кулинарный совет на русском",
    "image_prompt_en": "описание готового блюда на английском для генерации изображения"
  }}
}}

ВАЖНО: Верни ТОЛЬКО валидный JSON, без дополнительного текста!"""


def _format_date_russian(target_date: date) -> str:
    """Format date in Russian."""
    return f"{target_date.day} {MONTHS_RU[target_date.month]}"


def _get_weekday_russian(target_date: date) -> str:
    """Get weekday name in Russian."""
    return WEEKDAYS_RU[target_date.weekday()]


async def generate_post_content(
    target_date: date,
    holidays: List[Dict],
    quote: Dict
) -> Dict[str, Any]:
    """
    Generate complete post content using GPT-4o mini.
    
    Args:
        target_date: Date for the post
        holidays: List of holiday dictionaries from API
        quote: Quote dictionary with 'text' and 'author' keys
    
    Returns:
        Dictionary with greeting, holidays, holiday_text, and recipe
    """
    client = get_openai_client()
    settings = get_settings()
    
    # Get local food holidays
    local_holidays = get_food_holidays_for_date(target_date)
    
    # Combine with API holidays, prioritize food-related
    all_holidays = local_holidays + holidays
    
    # Format holidays for prompt
    if all_holidays:
        holidays_list = "\n".join([
            f"- {h.get('emoji', '🎉')} {h['name']}: {h.get('description', 'Кулинарный праздник')[:80]}"
            for h in all_holidays[:5]
        ])
    else:
        holidays_list = "- Сегодня нет кулинарных праздников в базе, придумай 3 интересных кулинарных события для этого дня"
    
    # Get recipe type from settings
    recipe_type = settings.recipe_type
    
    # Build system prompt with appropriate sweetener and recipe instructions
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        sweetener_prompt=_get_sweetener_prompt(recipe_type),
        recipe_type_prompt=_get_recipe_type_prompt(recipe_type)
    )
    
    # Create user prompt
    user_prompt = f"""Создай пост для {_format_date_russian(target_date)} ({_get_weekday_russian(target_date)}).

Известные кулинарные праздники на эту дату:
{holidays_list}

ЗАДАНИЕ:
1. Придумай уникальное тёплое приветствие (не просто "Доброе утро")
2. Опиши 3 кулинарных праздника с интересными фактами (если в списке мало - придумай подходящие)
3. Создай {recipe_type.upper()}-рецепт по теме ОДНОГО из праздников

ПОМНИ про правильное использование подсластителей!

Верни ТОЛЬКО валидный JSON!"""

    try:
        logger.info("Generating post content with GPT-4o mini...")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2500,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        logger.debug(f"GPT response: {content[:500]}...")
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate required fields
        if "greeting" not in result:
            result["greeting"] = "Доброе утро, мои дорогие! ☀️"
        
        # Format holiday_text from holidays array
        if "holidays" in result and isinstance(result["holidays"], list):
            holiday_parts = []
            for h in result["holidays"][:3]:
                emoji = h.get("emoji", "🎉")
                name = h.get("name", "")
                desc = h.get("description", "")
                holiday_parts.append(f"{emoji} <b>{name}</b> — {desc}")
            result["holiday_text"] = "\n".join(holiday_parts)
        else:
            result["holiday_text"] = result.get("holiday_text", "")
        
        # Validate recipe
        if "recipe" not in result:
            result["recipe"] = _get_static_fallback(target_date, quote)["recipe"]
        else:
            recipe = result["recipe"]
            required_fields = ["name", "servings", "cooking_time", "ingredients", "instructions", "image_prompt_en"]
            for field in required_fields:
                if field not in recipe:
                    if field == "image_prompt_en":
                        recipe["image_prompt_en"] = f"healthy {recipe.get('name', 'food')}"
                    elif field == "tip":
                        recipe["tip"] = ""
                    else:
                        raise ValueError(f"Missing recipe field: {field}")
        
        logger.info(f"Generated content for recipe: {result['recipe']['name']}")
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
    
    client = get_openai_client()
    settings = get_settings()
    
    simple_prompt = f"""Создай простой {settings.recipe_type.upper()}-рецепт на русском языке для {_format_date_russian(target_date)}.

Рецепт должен быть:
- Без сахара (используй эритрит: граммовка как у сахара, или стевию: 3-5 КАПЕЛЬ)
- С 5-6 ингредиентами
- С 5 шагами приготовления
- Время 15-30 минут

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
        
        # Get local holidays
        local_holidays = get_food_holidays_for_date(target_date)
        holiday_text = ""
        if local_holidays:
            holiday_parts = [f"{h.get('emoji', '🎉')} <b>{h['name']}</b>" for h in local_holidays[:3]]
            holiday_text = "Сегодня отмечаем:\n" + "\n".join(holiday_parts)
        else:
            holiday_text = f"Сегодня {_format_date_russian(target_date)} — отличный день для кулинарных экспериментов! 🍳✨"
        
        return {
            "greeting": f"Доброе утро, мои дорогие! ☀️ Пусть этот {_get_weekday_russian(target_date)} будет наполнен теплом и вкусной едой!",
            "holiday_text": holiday_text,
            "recipe": recipe
        }
        
    except Exception as e:
        logger.error(f"Fallback generation also failed: {e}")
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
            "calories_per_serving": 250,
            "ingredients": [
                "50г овсяных хлопьев",
                "1 яйцо",
                "50мл молока 1.5%",
                "50г свежих ягод",
                "15г эритрита (или 3-4 капли стевии)",
                "щепотка корицы"
            ],
            "instructions": [
                "Смешайте овсяные хлопья, яйцо и молоко в миске до однородности",
                "Добавьте эритрит (или стевию) и корицу, перемешайте",
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
                "content": "Напиши уникальное утреннее приветствие для кулинарного блога на русском языке. 1-2 предложения с эмодзи. Тёплое и дружелюбное. Не начинай просто с 'Доброе утро' - сделай интереснее."
            }],
            max_tokens=100,
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating greeting: {e}")
        return "Доброе утро, мои дорогие! ☀️ Пусть этот день будет наполнен вкусной и полезной едой!"


async def generate_recipe(holiday_name: str, recipe_type: str = "pp") -> Dict[str, Any]:
    """
    Generate a recipe for a specific holiday.
    
    Args:
        holiday_name: Name of the holiday to create recipe for
        recipe_type: Type of recipe (pp, keto, mixed)
    
    Returns:
        Recipe dictionary
    """
    client = get_openai_client()
    
    sweetener_note = _get_sweetener_prompt(recipe_type)
    recipe_reqs = _get_recipe_type_prompt(recipe_type)
    
    prompt = f"""Создай рецепт для праздника "{holiday_name}".

{sweetener_note}

{recipe_reqs}

Требования:
- 3-8 ингредиентов с точными граммовками
- 5-10 понятных шагов
- Реалистичный рецепт

Верни JSON:
{{"name": "название рецепта", "servings": число, "cooking_time": минуты, "calories_per_serving": калории, "ingredients": ["ингредиент с граммовкой"], "instructions": ["шаг"], "tip": "совет", "image_prompt_en": "описание блюда на английском"}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        return _get_static_fallback(date.today(), {})["recipe"]


async def analyze_image_for_post(
    image_base64: str,
    category: str = "pp"
) -> Dict[str, Any]:
    """
    Analyze an image and generate a post based on it.
    
    Args:
        image_base64: Base64 encoded image
        category: Category for the post (pp, keto, culinary)
    
    Returns:
        Dictionary with post content
    """
    client = get_openai_client()
    
    category_prompts = {
        "pp": "ПП (правильное питание) — полезный рецепт без сахара",
        "keto": "Кето — низкоуглеводный рецепт с высоким содержанием жиров",
        "culinary": "Кулинарный — классический рецепт с историей блюда",
        "breakfast": "Завтрак — утренний рецепт, бодрящий и питательный",
        "dessert": "Десерт — сладкое без сахара, полезная версия"
    }
    
    category_desc = category_prompts.get(category, category_prompts["pp"])
    
    prompt = f"""Посмотри на это изображение еды и создай пост для кулинарного канала.

Категория: {category_desc}

Создай JSON с:
1. Название блюда на русском
2. Краткое описание (2-3 предложения)
3. Рецепт (если можешь определить ингредиенты)
4. Интересный факт о блюде

Формат JSON:
{{
  "dish_name": "название",
  "description": "описание блюда и его особенностей",
  "recipe": {{
    "name": "название",
    "servings": 4,
    "cooking_time": 30,
    "ingredients": ["ингредиент 1", "..."],
    "instructions": ["шаг 1", "..."],
    "tip": "совет"
  }},
  "fun_fact": "интересный факт",
  "hashtags": ["#хэштег1", "#хэштег2"]
}}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return {
            "error": str(e),
            "dish_name": "Не удалось распознать",
            "description": "Попробуйте другое изображение"
        }
