"""
Callback handlers for inline keyboard buttons.
Handles all callback queries from inline keyboards.
"""

import logging
from datetime import datetime, date

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from config import config
from keyboards import (
    main_menu_keyboard, 
    settings_keyboard, 
    schedule_keyboard,
    back_keyboard,
    model_select_keyboard,
    template_select_keyboard,
    preview_post_keyboard,
    neural_tests_keyboard,
    confirm_image_test_keyboard,
    new_post_category_keyboard,
    recipe_category_keyboard,
    recipe_confirm_keyboard,
    cancel_keyboard,
    skip_keyboard
)
from handlers.states import (
    ScheduleStates,
    TemplateStates,
    NewPostStates,
    EditPostStates,
    RecipeStates,
    PollStates,
    TipStates,
    LifehackStates
)
from services.user_service import update_user_activity, format_user_stats
from services.settings_service import (
    get_settings, 
    update_settings, 
    TextTemplate, 
    ImageModel
)
from utils.logger import mask_user_id, mask_channel_id

logger = logging.getLogger(__name__)
router = Router(name="callbacks")


def is_admin(user_id: int) -> bool:
    """Check if user is authorized admin."""
    return config.is_admin(user_id)


async def answer_unauthorized(callback: CallbackQuery) -> None:
    """Answer callback for unauthorized users."""
    await callback.answer("❌ У вас нет доступа", show_alert=True)
    logger.warning(f"Unauthorized callback from {mask_user_id(callback.from_user.id, config.debug_mode)}")


# ============================================
# SETTINGS MENU CALLBACKS
# ============================================

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery) -> None:
    """Handle 'Назад' button from settings - return to main menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_back_main"
        )
        
        main_text = """
🍽 <b>Utro Bot</b>

Используйте кнопки меню для управления ботом.

• 📨 <b>Пост сейчас</b> — отправить пост в канал
• 📊 <b>Статус</b> — информация о боте
• ⚙️ <b>Настройки</b> — настройки и тесты
• ℹ️ <b>Помощь</b> — справка
"""
        await callback.message.edit_text(
            main_text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in cb_back_main: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "back_settings")
async def cb_back_settings(callback: CallbackQuery) -> None:
    """Handle 'Назад' button - return to settings menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        from services.settings_service import get_settings
        settings = get_settings()
        
        img_status = "вкл" if settings.image_enabled else "выкл"
        model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
        
        settings_text = f"""
⚙️ <b>Настройки</b>

<b>Текущие параметры:</b>
🖼 Изображение: {img_status}
🎨 Модель: {model_name}
📝 Шаблон: {settings.text_template}

Выберите настройку для изменения:
"""
        await callback.message.edit_text(
            settings_text,
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_back_settings: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "schedule")
async def cb_schedule(callback: CallbackQuery) -> None:
    """Handle 'Расписание' button - show schedule settings."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_schedule"
        )
        
        current_time = config.morning_post_time
        schedule_text = f"""
⏰ <b>Расписание постинга</b>

<b>Текущее время:</b> {current_time} (МСК)

Выберите новое время:
"""
        await callback.message.edit_text(
            schedule_text,
            parse_mode="HTML",
            reply_markup=schedule_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_schedule: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# NEW SETTINGS CALLBACKS (v2)
# ============================================

@router.callback_query(F.data == "settings:image_toggle")
async def cb_image_toggle(callback: CallbackQuery) -> None:
    """Toggle image generation on/off."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        settings = get_settings()
        new_value = not settings.image_enabled
        update_settings(image_enabled=new_value)
        
        status = "✅ вкл" if new_value else "❌ выкл"
        await callback.answer(f"Изображение: {status}")
        
        await callback.message.edit_reply_markup(reply_markup=settings_keyboard())
        
    except Exception as e:
        logger.error(f"Error in cb_image_toggle: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "settings:neural_tests")
async def cb_neural_tests(callback: CallbackQuery) -> None:
    """Show neural network tests submenu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "🧪 <b>Тест нейросетей</b>\n\n"
            "Выберите тест:",
            parse_mode="HTML",
            reply_markup=neural_tests_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_neural_tests: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "test_image_confirm")
async def cb_test_image_confirm(callback: CallbackQuery) -> None:
    """Show confirmation before generating test image."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        settings = get_settings()
        model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
        cost = "~$0.04" if settings.image_model == ImageModel.DALLE3.value else "~$0.003"
        
        await callback.message.edit_text(
            f"🖼 <b>Тест генерации изображения</b>\n\n"
            f"<b>Модель:</b> {model_name}\n"
            f"<b>Стоимость:</b> {cost}\n\n"
            f"Будет сгенерировано тестовое изображение блюда.\n"
            f"Продолжить?",
            parse_mode="HTML",
            reply_markup=confirm_image_test_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_test_image_confirm: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "test_image_run")
async def cb_test_image_run(callback: CallbackQuery) -> None:
    """Generate test image with selected model."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        settings = get_settings()
        model_name = "DALL-E 3" if settings.image_model == ImageModel.DALLE3.value else "Flux"
        
        await callback.answer(f"🎨 Генерирую ({model_name})...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="test_image_run"
        )
        
        await callback.message.edit_text(
            f"🎨 <b>Генерирую тестовое изображение...</b>\n\n"
            f"Модель: {model_name}\n"
            f"Это может занять 30-60 секунд.",
            parse_mode="HTML"
        )
        
        # Generate image using current model
        from services.image_generator import generate_food_image
        image_bytes = await generate_food_image(
            recipe_name="Тестовое изображение",
            english_prompt="healthy colorful salad bowl with fresh vegetables, appetizing food photography"
        )
        
        if image_bytes:
            photo = BufferedInputFile(image_bytes, filename=f"test_{model_name.lower().replace(' ', '_')}.jpg")
            await callback.message.answer_photo(
                photo=photo,
                caption=f"🎨 <b>Тестовое изображение</b>\n\n"
                        f"✅ Модель: {model_name}\n"
                        f"Генерация работает корректно!",
                parse_mode="HTML"
            )
            
            await callback.message.edit_text(
                "✅ <b>Изображение сгенерировано!</b>\n\nСмотрите выше ⬆️",
                parse_mode="HTML",
                reply_markup=neural_tests_keyboard()
            )
            
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested {model_name}")
        else:
            await callback.message.edit_text(
                f"❌ <b>Не удалось сгенерировать</b>\n\n"
                f"Проверьте API ключ и баланс для {model_name}.",
                parse_mode="HTML",
                reply_markup=neural_tests_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in cb_test_image_run: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=neural_tests_keyboard()
        )


@router.callback_query(F.data == "settings:model_select")
async def cb_model_select(callback: CallbackQuery) -> None:
    """Show model selection menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "🎨 <b>Выбор модели генерации изображений</b>\n\n"
            "• <b>DALL-E 3</b> — Высокое качество, OpenAI\n"
            "• <b>Flux</b> — Быстрая генерация, Together AI\n\n"
            "Выберите модель:",
            parse_mode="HTML",
            reply_markup=model_select_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_model_select: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("model:"))
async def cb_select_model(callback: CallbackQuery) -> None:
    """Handle model selection."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        model = callback.data.split(":")[1]
        update_settings(image_model=model)
        
        model_name = "DALL-E 3" if model == ImageModel.DALLE3.value else "Flux"
        await callback.answer(f"Модель: {model_name}")
        
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\nВыберите параметр:",
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_select_model: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "settings:template_select")
async def cb_template_select(callback: CallbackQuery) -> None:
    """Show template selection menu."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "📝 <b>Выбор длины поста</b>\n\n"
            "• <b>Короткий</b> (~800 символов) — Компактный пост\n"
            "• <b>Средний</b> (~1000 символов) — Стандартный\n"
            "• <b>Длинный</b> (~2000 символов) — Подробный\n"
            "• <b>Свой</b> — Указать количество символов\n\n"
            "Выберите шаблон:",
            parse_mode="HTML",
            reply_markup=template_select_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_template_select: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("template:"))
async def cb_select_template(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle template selection."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        template = callback.data.split(":")[1]
        
        if template == "custom_length":
            # Enter FSM state for custom length input
            await state.set_state(TemplateStates.waiting_for_custom_length)
            await callback.answer()
            await callback.message.edit_text(
                "🔢 <b>Своя длина поста</b>\n\n"
                "Отправьте желаемое количество символов.\n"
                "Допустимый диапазон: 100 — 5000\n\n"
                "Например: <code>1500</code>",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "Жду число символов...",
                reply_markup=cancel_keyboard()
            )
            return
        
        if template == "CUSTOM":
            # Enter FSM state for custom template text
            await state.set_state(TemplateStates.waiting_for_custom_template)
            await callback.answer()
            await callback.message.edit_text(
                "✏️ <b>Свой шаблон</b>\n\n"
                "Опишите формат постов, который вам нужен.\n\n"
                "<i>Примеры:</i>\n"
                "• «Начинай с эмодзи, потом заголовок, потом рецепт списком»\n"
                "• «Короткий совет + интересный факт в конце»\n"
                "• «Формат: название, время готовки, ингредиенты, шаги»",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "Жду описание шаблона...",
                reply_markup=cancel_keyboard()
            )
            return
        
        update_settings(text_template=template)
        
        template_names = {
            "SHORT": "Короткий (~500)",
            "MEDIUM": "Средний (~900)",
            "LONG": "Длинный (~1800)"
        }
        await callback.answer(f"✅ {template_names.get(template, template)}")
        
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\nВыберите параметр:",
            parse_mode="HTML",
            reply_markup=settings_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_select_template: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(callback: CallbackQuery) -> None:
    """Universal cancel handler."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    await callback.answer("Отменено")
    await callback.message.edit_text(
        "✅ Действие отменено",
        reply_markup=None
    )


@router.callback_query(F.data.startswith("set_time_"))
async def cb_set_time_legacy(callback: CallbackQuery) -> None:
    """Handle legacy time selection buttons."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        hour = callback.data.replace("set_time_", "")
        await callback.answer(
            f"⏰ Для изменения времени на {hour}:00 отредактируйте .env файл:\n"
            f"MORNING_POST_TIME={hour}:00",
            show_alert=True
        )
        
    except Exception as e:
        logger.error(f"Error in cb_set_time: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("set_time:"))
async def cb_set_time_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle new time selection buttons."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        time_value = callback.data.split(":")[1]
        
        if time_value == "custom":
            # Enter FSM state for custom time input
            await state.set_state(ScheduleStates.waiting_for_custom_time)
            await callback.answer()
            await callback.message.edit_text(
                "🕐 <b>Своё время постинга</b>\n\n"
                "Отправьте время в формате ЧЧ:ММ\n"
                "Например: <code>06:30</code> или <code>11:45</code>\n\n"
                "Отправьте /cancel для отмены.",
                parse_mode="HTML"
            )
        else:
            # Direct time selection
            if len(time_value) == 2:
                time_value = f"{time_value}:00"
            
            await callback.answer(
                f"⏰ Для изменения времени на {time_value}\n"
                f"отредактируйте MORNING_POST_TIME в .env файле.",
                show_alert=True
            )
        
    except Exception as e:
        logger.error(f"Error in cb_set_time_new: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# NEW POST FLOW CALLBACKS (v3)
# ============================================

@router.callback_query(F.data == "newpost:recipe")
async def cb_newpost_recipe(callback: CallbackQuery) -> None:
    """Show recipe category selection."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        await callback.message.edit_text(
            "🍳 <b>Выберите тип рецепта</b>\n\n"
            "Бот сгенерирует пост с рецептом выбранной категории:",
            parse_mode="HTML",
            reply_markup=recipe_category_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_recipe: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "newpost:custom")
async def cb_newpost_custom(callback: CallbackQuery, state: FSMContext) -> None:
    """Start custom post creation - enter FSM for content input."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        # Store category and enter content input state
        await state.update_data(category="custom")
        await state.set_state(NewPostStates.waiting_for_content)
        
        await callback.message.edit_text(
            "💡 <b>Своя идея</b>\n\n"
            "Отправьте идею для поста:\n"
            "• Фото с подписью 📷\n"
            "• Или просто текст\n"
            "• Или фото отдельно\n\n"
            "<i>Если отправите фото с подписью — бот использует оба!</i>",
            parse_mode="HTML"
        )
        
        # Send cancel keyboard
        await callback.message.answer(
            "Жду вашу идею...",
            reply_markup=cancel_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} started custom post flow")
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_custom: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "newpost:back")
async def cb_newpost_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to new post category selection."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        # Clear any FSM state
        await state.clear()
        await callback.answer()
        
        await callback.message.edit_text(
            "✨ <b>Новый пост</b>\n\n"
            "Выберите тип поста:",
            parse_mode="HTML",
            reply_markup=new_post_category_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_back: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# NEW POST CATEGORIES (Poll, Tip, Lifehack)
# ============================================

@router.callback_query(F.data == "newpost:poll")
async def cb_newpost_poll(callback: CallbackQuery, state: FSMContext) -> None:
    """Start poll creation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        await state.update_data(category="poll")
        await state.set_state(PollStates.waiting_for_topic)
        
        await callback.message.edit_text(
            "📊 <b>Создание опроса</b>\n\n"
            "Напишите тему опроса или нажмите «Пропустить» для автогенерации.\n\n"
            "<i>Примеры:</i>\n"
            "• Какой завтрак вы предпочитаете?\n"
            "• Лучшая кухня мира?\n"
            "• Сладкое или солёное?",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Жду тему опроса...",
            reply_markup=skip_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_poll: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "newpost:tip")
async def cb_newpost_tip(callback: CallbackQuery, state: FSMContext) -> None:
    """Start cooking tip creation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        await state.update_data(category="tip")
        await state.set_state(TipStates.waiting_for_topic)
        
        await callback.message.edit_text(
            "💡 <b>Кулинарный совет</b>\n\n"
            "Напишите тему совета или нажмите «Пропустить».\n\n"
            "<i>Примеры:</i>\n"
            "• Как правильно варить рис\n"
            "• Секреты сочного мяса\n"
            "• Как хранить зелень",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Жду тему совета...",
            reply_markup=skip_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_tip: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "newpost:lifehack")
async def cb_newpost_lifehack(callback: CallbackQuery, state: FSMContext) -> None:
    """Start kitchen lifehack creation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        await state.update_data(category="lifehack")
        await state.set_state(LifehackStates.waiting_for_topic)
        
        await callback.message.edit_text(
            "🔧 <b>Кухонный лайфхак</b>\n\n"
            "Напишите тему лайфхака или нажмите «Пропустить».\n\n"
            "<i>Примеры:</i>\n"
            "• Как быстро почистить чеснок\n"
            "• Лайфхаки с микроволновкой\n"
            "• Как сохранить продукты свежими",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Жду тему лайфхака...",
            reply_markup=skip_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_lifehack: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("recipe:"))
async def cb_recipe_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle recipe category selection - show confirmation step."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        category = callback.data.split(":")[1]
        
        category_names = {
            "pp": "🥗 ПП",
            "keto": "🥑 Кето",
            "vegan": "🌱 Веган",
            "detox": "🍵 Детокс",
            "breakfast": "🍳 Завтраки",
            "dessert": "🍰 ПП-десерты",
            "smoothie": "🥤 Смузи",
            "soup": "🥣 Супы"
        }
        
        category_name = category_names.get(category, category)
        
        # Save category to state for confirmation step
        await state.update_data(recipe_category=category)
        await state.set_state(RecipeStates.confirming)
        
        await callback.answer()
        
        # Show confirmation with options
        await callback.message.edit_text(
            f"📂 <b>Категория: {category_name}</b>\n\n"
            f"Выберите действие:\n"
            f"• <b>Сгенерировать</b> — сразу создать пост\n"
            f"• <b>Добавить идею</b> — уточнить рецепт\n"
            f"• <b>Добавить фото</b> — использовать своё фото",
            parse_mode="HTML",
            reply_markup=recipe_confirm_keyboard(category)
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} selected recipe: {category}")
        
    except Exception as e:
        logger.error(f"Error in cb_recipe_category: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("recipe_gen:"))
async def cb_recipe_generate(callback: CallbackQuery, state: FSMContext) -> None:
    """Generate recipe with current settings."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        category = callback.data.split(":")[1]
        data = await state.get_data()
        custom_idea = data.get("recipe_idea")
        
        category_names = {
            "pp": "ПП",
            "keto": "Кето",
            "vegan": "Веган",
            "detox": "Детокс",
            "breakfast": "Завтраки",
            "dessert": "ПП-десерты",
            "smoothie": "Смузи",
            "soup": "Супы"
        }
        category_name = category_names.get(category, category)
        
        await callback.answer(f"🍳 Генерирую {category_name} рецепт...")
        await state.clear()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action=f"recipe_{category}"
        )
        
        await callback.message.edit_text(
            f"⏳ <b>Генерирую {category_name} рецепт...</b>\n\n"
            f"{'📝 С идеей: ' + custom_idea[:50] + '...' if custom_idea else ''}\n"
            f"Это может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        # Generate recipe post
        from services.post_service import post_to_channel
        
        success, post_id = await post_to_channel(
            bot=callback.bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=callback.from_user.id,
            recipe_category=category,
            custom_idea=custom_idea
        )
        
        if success and post_id:
            try:
                await callback.message.delete()
            except:
                pass
            logger.info(f"Recipe post ({category}) generated: {post_id}")
        else:
            await callback.message.edit_text(
                f"❌ <b>Не удалось сгенерировать {category_name} рецепт</b>\n\n"
                f"Попробуйте позже.",
                parse_mode="HTML",
                reply_markup=recipe_category_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in cb_recipe_generate: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("recipe_idea:"))
async def cb_recipe_add_idea(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask for custom idea for recipe."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        category = callback.data.split(":")[1]
        await state.update_data(recipe_category=category)
        await state.set_state(RecipeStates.waiting_for_custom_idea)
        
        await callback.answer()
        
        await callback.message.edit_text(
            "✏️ <b>Добавьте свою идею</b>\n\n"
            "Напишите, какой именно рецепт вы хотите.\n\n"
            "<i>Например:</i>\n"
            "• Паста с морепродуктами\n"
            "• Быстрый завтрак за 5 минут\n"
            "• Что-то с авокадо",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Жду вашу идею...",
            reply_markup=cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_recipe_add_idea: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("recipe_photo:"))
async def cb_recipe_add_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask for custom photo for recipe."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        category = callback.data.split(":")[1]
        await state.update_data(recipe_category=category)
        await state.set_state(RecipeStates.waiting_for_custom_photo)
        
        await callback.answer()
        
        await callback.message.edit_text(
            "📷 <b>Отправьте фото</b>\n\n"
            "Это фото будет использовано вместо сгенерированного.",
            parse_mode="HTML"
        )
        
        await callback.message.answer(
            "Жду фото...",
            reply_markup=cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_recipe_add_photo: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)
                f"❌ <b>Не удалось сгенерировать {category_name} рецепт</b>\n\n"
                f"Попробуйте позже.",
                parse_mode="HTML",
                reply_markup=recipe_category_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in cb_recipe_category: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# NEW POST PROMPT CALLBACKS
# ============================================

@router.callback_query(F.data == "newpost_prompt:custom")
async def cb_newpost_prompt_custom(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to provide custom prompt."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        await state.set_state(NewPostStates.waiting_for_prompt)
        
        await callback.message.edit_text(
            "✏️ <b>Введите промпт</b>\n\n"
            "Опишите, что именно должно быть в посте.\n"
            "Бот учтёт ваши пожелания при генерации.\n\n"
            "Отправьте /cancel для отмены.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in cb_newpost_prompt_custom: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "newpost_prompt:auto")
async def cb_newpost_prompt_auto(callback: CallbackQuery, state: FSMContext) -> None:
    """User chose automatic generation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("⏳ Генерирую...")
        
        # Get stored data and generate
        data = await state.get_data()
        category = data.get("category", "pp")
        user_idea = data.get("user_idea", "")
        
        await state.clear()
        
        await callback.message.edit_text(
            "⏳ <b>Генерирую пост...</b>\n\n"
            "Это может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        from services.post_service import post_to_channel
        
        success, post_id = await post_to_channel(
            bot=callback.bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=callback.from_user.id,
            recipe_category=category,
            custom_idea=user_idea if user_idea else None
        )
        
        if success and post_id:
            try:
                await callback.message.delete()
            except:
                pass
            logger.info(f"Auto post generated: {post_id}")
        else:
            await callback.message.edit_text(
                "❌ Не удалось сгенерировать пост. Попробуйте позже.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Error in cb_newpost_prompt_auto: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# TEST CALLBACKS
# ============================================

@router.callback_query(F.data == "test_holidays")
async def cb_test_holidays(callback: CallbackQuery) -> None:
    """Handle 'Тест праздников' button - test holidays from JSON."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🔍 Загружаю праздники...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_holidays"
        )
        
        # Show loading state
        await callback.message.edit_text(
            "🔍 <b>Загружаю праздники...</b>",
            parse_mode="HTML"
        )
        
        # Fetch holidays from JSON
        from services.holidays_api import fetch_holidays_for_date
        today = date.today()
        holidays = await fetch_holidays_for_date(today)
        
        if holidays:
            holidays_text = f"🎉 <b>Праздники на {today.strftime('%d.%m.%Y')}:</b>\n\n"
            
            for i, holiday in enumerate(holidays[:5], 1):
                name = holiday.get("name", "Без названия")
                holidays_text += f"{i}. {name}\n"
            
            if len(holidays) > 5:
                holidays_text += f"\n... и ещё {len(holidays) - 5}"
            
            holidays_text += f"\n\n✅ <b>Всего:</b> {len(holidays)} праздников"
        else:
            holidays_text = "❌ <b>Праздники не найдены</b>\n\nПроверьте файл data/food_holidays.json"
        
        await callback.message.edit_text(
            holidays_text,
            parse_mode="HTML",
            reply_markup=neural_tests_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested holidays: {len(holidays) if holidays else 0} found")
        
    except Exception as e:
        logger.error(f"Error in cb_test_holidays: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=neural_tests_keyboard()
        )


@router.callback_query(F.data == "test_gpt")
async def cb_test_gpt(callback: CallbackQuery) -> None:
    """Handle 'Тест GPT-4o mini' button - test AI content generation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🤖 Генерирую контент...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_gpt"
        )
        
        await callback.message.edit_text(
            "🤖 <b>Генерирую тестовый контент...</b>\n\n"
            "Это может занять 10-30 секунд.",
            parse_mode="HTML"
        )
        
        # Generate content
        from services.ai_content import generate_greeting
        greeting = await generate_greeting()
        
        result_text = f"""
🤖 <b>Тест GPT-4o mini</b>

<b>Сгенерированное приветствие:</b>

{greeting}

✅ <i>AI работает корректно!</i>
"""
        
        await callback.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested GPT-4o mini")
        
    except Exception as e:
        logger.error(f"Error in cb_test_gpt: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка GPT-4o mini:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )


@router.callback_query(F.data == "test_dalle")
async def cb_test_dalle(callback: CallbackQuery) -> None:
    """Handle 'Тест DALL-E' button - generate test image."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🎨 Генерирую изображение...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_test_dalle"
        )
        
        await callback.message.edit_text(
            "🎨 <b>Генерирую тестовое изображение...</b>\n\n"
            "Это может занять 30-60 секунд.\n"
            "Стоимость: ~$0.04",
            parse_mode="HTML"
        )
        
        # Generate image
        from services.image_generator import generate_food_image
        image_bytes = await generate_food_image(
            recipe_name="Test Image",
            english_prompt="healthy colorful salad bowl, appetizing"
        )
        
        if image_bytes:
            # Send image
            photo = BufferedInputFile(image_bytes, filename="test_dalle.jpg")
            await callback.message.answer_photo(
                photo=photo,
                caption="🎨 <b>Тестовое изображение DALL-E 3</b>\n\n✅ Генерация работает корректно!",
                parse_mode="HTML"
            )
            
            # Edit original message
            await callback.message.edit_text(
                "✅ <b>Изображение сгенерировано!</b>\n\n"
                "Смотрите выше ⬆️",
                parse_mode="HTML",
                reply_markup=back_keyboard()
            )
            
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} tested DALL-E 3 successfully")
        else:
            await callback.message.edit_text(
                "❌ <b>Не удалось сгенерировать изображение</b>\n\n"
                "Проверьте баланс OpenAI и API ключ.",
                parse_mode="HTML",
                reply_markup=back_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in cb_test_dalle: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка DALL-E:</b>\n\n{str(e)[:200]}",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )


@router.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery) -> None:
    """Handle 'Моя статистика' button - show user stats."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_my_stats"
        )
        
        stats_text = format_user_stats(callback.from_user.id)
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} viewed their stats")
        
    except Exception as e:
        logger.error(f"Error in cb_my_stats: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# POST CONFIRMATION CALLBACKS
# ============================================

@router.callback_query(F.data == "confirm_post")
async def cb_confirm_post(callback: CallbackQuery) -> None:
    """Handle post confirmation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("📤 Отправляю пост...")
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cb_confirm_post"
        )
        
        await callback.message.edit_text(
            "⏳ <b>Генерирую и отправляю пост...</b>\n\n"
            "Это может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        from services.post_service import post_to_channel
        from handlers.admin import update_last_post_status
        from services.user_service import increment_posts_triggered
        
        bot = callback.message.bot
        success = await post_to_channel(bot, config.channel_id)
        
        if success:
            update_last_post_status(success=True)
            increment_posts_triggered(callback.from_user.id)
            await callback.message.edit_text(
                "✅ <b>Пост успешно опубликован!</b>",
                parse_mode="HTML"
            )
        else:
            update_last_post_status(success=False, error="Post failed")
            await callback.message.edit_text(
                "❌ <b>Не удалось опубликовать пост.</b>\n\n"
                "Проверьте логи для деталей.",
                parse_mode="HTML"
            )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} confirmed post: {'success' if success else 'failed'}")
        
    except Exception as e:
        logger.error(f"Error in cb_confirm_post: {e}", exc_info=True)
        await callback.message.edit_text(
            f"⚠️ <b>Ошибка:</b> {str(e)[:100]}",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "cancel_post")
async def cb_cancel_post(callback: CallbackQuery) -> None:
    """Handle post cancellation."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("Отменено")
        
        await callback.message.edit_text(
            "❌ <b>Отправка поста отменена.</b>",
            parse_mode="HTML"
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} cancelled post")
        
    except Exception as e:
        logger.error(f"Error in cb_cancel_post: {e}", exc_info=True)


# ============================================
# LEGACY ADMIN CALLBACKS (for compatibility)
# ============================================

@router.callback_query(F.data == "admin_post_now")
async def cb_admin_post_now(callback: CallbackQuery) -> None:
    """Legacy callback for admin post button."""
    await cb_confirm_post(callback)


@router.callback_query(F.data == "admin_status")
async def cb_admin_status(callback: CallbackQuery) -> None:
    """Legacy callback for admin status button."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer()
        
        # Import and call status logic
        from handlers.admin import bot_start_time, last_post_status
        
        uptime = datetime.now() - bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        status_text = f"""
📊 <b>Статус бота</b>

⏱ <b>Аптайм:</b> {days}д {hours}ч {minutes}м
📅 <b>Время поста:</b> {config.morning_post_time} (МСК)
📢 <b>Канал:</b> {mask_channel_id(config.channel_id, config.debug_mode)}
"""
        
        await callback.message.edit_text(
            status_text,
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in cb_admin_status: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_test_holidays")
async def cb_admin_test_holidays(callback: CallbackQuery) -> None:
    """Legacy callback for admin test holidays button."""
    await cb_test_holidays(callback)


# ============================================
# POST PREVIEW CALLBACKS (New format)
# ============================================

@router.callback_query(F.data.startswith("publish:"))
async def cb_publish_new(callback: CallbackQuery) -> None:
    """Handle '✅ Опубликовать' button - publish pending post (new format)."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        post_id = callback.data.split(":")[1]
        await callback.answer("📤 Публикую в канал...")
        
        from services.post_service import publish_pending_post
        from services.user_service import increment_posts_triggered
        from handlers.admin import update_last_post_status
        
        success = await publish_pending_post(
            bot=callback.bot,
            post_id=post_id,
            channel_id=config.channel_id
        )
        
        if success:
            update_last_post_status(success=True)
            increment_posts_triggered(callback.from_user.id)
            
            await callback.message.edit_caption(
                caption="✅ <b>Пост успешно опубликован!</b>",
                parse_mode="HTML"
            )
            logger.info(f"Post {post_id} published by {mask_user_id(callback.from_user.id, config.debug_mode)}")
        else:
            update_last_post_status(success=False, error="Publish failed")
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось опубликовать.</b>\nПроверьте логи.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Error in cb_publish_new: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при публикации", show_alert=True)


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit_post(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle '✏️ Редактировать' button - start editing post text."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        post_id = callback.data.split(":")[1]
        
        from services.post_service import get_pending_post
        from keyboards import editing_keyboard
        
        post_data = get_pending_post(post_id)
        if not post_data:
            await callback.answer("Пост не найден", show_alert=True)
            return
        
        # Check if multi-post
        is_multipost = post_data.get("is_multipost", False)
        total_parts = post_data.get("total_parts", 1)
        
        if is_multipost and total_parts > 1:
            # Ask which part to edit
            await state.update_data(editing_post_id=post_id, total_parts=total_parts)
            await state.set_state(EditPostStates.selecting_part)
            
            await callback.answer()
            await callback.message.answer(
                f"✏️ <b>Редактирование мульти-поста</b>\n\n"
                f"Пост разделён на {total_parts} части.\n"
                f"Введите номер части для редактирования (1-{total_parts}):\n\n"
                f"Отправьте /cancel для отмены.",
                parse_mode="HTML"
            )
        else:
            # Single post - direct edit
            await state.update_data(editing_post_id=post_id)
            await state.set_state(EditPostStates.waiting_for_new_text)
            
            await callback.answer()
            await callback.message.answer(
                "✏️ <b>Режим редактирования</b>\n\n"
                "Отправьте новый текст поста целиком.\n"
                "Текущий текст будет заменён.\n\n"
                "Отправьте /cancel для отмены.",
                parse_mode="HTML",
                reply_markup=editing_keyboard()
            )
        
        logger.info(f"Editing started for post {post_id}")
        
    except Exception as e:
        logger.error(f"Error in cb_edit_post: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("regenerate:"))
async def cb_regenerate_new(callback: CallbackQuery) -> None:
    """Handle '🔄 Заново' button - regenerate post (new format)."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        post_id = callback.data.split(":")[1]
        await callback.answer("🔄 Генерирую заново...")
        
        from services.post_service import generate_post_data, store_pending_post, _pending_posts
        
        # Show loading
        try:
            await callback.message.edit_caption(
                caption="⏳ <b>Генерирую новый пост...</b>",
                parse_mode="HTML"
            )
        except:
            pass
        
        # Generate new post
        post_data = await generate_post_data()
        
        if post_data:
            # Replace with same ID
            _pending_posts[post_id] = post_data
            
            # Send new preview
            from services.post_service import send_preview_to_admin
            await send_preview_to_admin(
                bot=callback.bot,
                admin_id=callback.from_user.id,
                post_data=post_data,
                reply_markup=preview_post_keyboard(post_id)
            )
            
            try:
                await callback.message.delete()
            except:
                pass
        else:
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось перегенерировать</b>",
                parse_mode="HTML",
                reply_markup=preview_post_keyboard(post_id)
            )
            
    except Exception as e:
        logger.error(f"Error in cb_regenerate_new: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel_new(callback: CallbackQuery) -> None:
    """Handle '❌ Отменить' button - cancel pending post (new format)."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        post_id = callback.data.split(":")[1]
        
        from services.post_service import remove_pending_post
        remove_pending_post(post_id)
        
        await callback.answer("Отменено")
        await callback.message.edit_caption(
            caption="❌ <b>Публикация отменена</b>",
            parse_mode="HTML"
        )
        
        logger.info(f"Post {post_id} cancelled")
        
    except Exception as e:
        logger.error(f"Error in cb_cancel_new: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


# ============================================
# POST PREVIEW CALLBACKS (Legacy format)
# ============================================

@router.callback_query(F.data.startswith("publish_post"))
async def cb_publish_post(callback: CallbackQuery) -> None:
    """Handle '✅ Опубликовать в канал' button - publish pending post."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("📤 Публикую в канал...")
        
        # Extract post_id from callback data
        parts = callback.data.split(":")
        post_id = parts[1] if len(parts) > 1 else ""
        
        if not post_id:
            await callback.message.edit_caption(
                caption="❌ <b>Ошибка:</b> Пост не найден.\n\nПопробуйте сгенерировать новый.",
                parse_mode="HTML"
            )
            return
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="publish_post"
        )
        
        # Publish the pending post
        from services.post_service import publish_pending_post
        from services.user_service import increment_posts_triggered
        from handlers.admin import update_last_post_status
        
        success = await publish_pending_post(
            bot=callback.bot,
            post_id=post_id,
            channel_id=config.channel_id
        )
        
        if success:
            update_last_post_status(success=True)
            increment_posts_triggered(callback.from_user.id)
            
            # Update the preview message
            await callback.message.edit_caption(
                caption="✅ <b>Пост успешно опубликован в канале!</b>",
                parse_mode="HTML"
            )
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} published post {post_id}")
        else:
            update_last_post_status(success=False, error="Publish failed")
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось опубликовать пост.</b>\n\nПроверьте логи для деталей.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in cb_publish_post: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при публикации", show_alert=True)


@router.callback_query(F.data.startswith("cancel_preview"))
async def cb_cancel_preview(callback: CallbackQuery) -> None:
    """Handle '❌ Отменить' button - cancel pending post."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("Отменено")
        
        # Extract post_id from callback data
        parts = callback.data.split(":")
        post_id = parts[1] if len(parts) > 1 else ""
        
        # Remove pending post if exists
        if post_id:
            from services.post_service import remove_pending_post
            remove_pending_post(post_id)
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="cancel_preview"
        )
        
        # Update the preview message
        await callback.message.edit_caption(
            caption="❌ <b>Публикация отменена</b>\n\nИспользуйте меню для создания нового поста.",
            parse_mode="HTML"
        )
        
        logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} cancelled preview")
        
    except Exception as e:
        logger.error(f"Error in cb_cancel_preview: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("regenerate_post"))
async def cb_regenerate_post(callback: CallbackQuery) -> None:
    """Handle '🔄 Регенерировать' button - generate new post content."""
    if not is_admin(callback.from_user.id):
        await answer_unauthorized(callback)
        return
    
    try:
        await callback.answer("🔄 Генерирую новый пост...")
        
        # Extract old post_id and remove it
        parts = callback.data.split(":")
        old_post_id = parts[1] if len(parts) > 1 else ""
        
        if old_post_id:
            from services.post_service import remove_pending_post
            remove_pending_post(old_post_id)
        
        update_user_activity(
            user_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
            action="regenerate_post"
        )
        
        # Update message to show loading
        await callback.message.edit_caption(
            caption="🔄 <b>Генерирую новый пост...</b>\n\nЭто может занять 1-2 минуты.",
            parse_mode="HTML"
        )
        
        # Generate new post with preview
        from services.post_service import post_to_channel
        from keyboards import preview_post_keyboard
        
        success, new_post_id = await post_to_channel(
            bot=callback.bot,
            channel_id=config.channel_id,
            preview_mode=True,
            admin_id=callback.from_user.id
        )
        
        if success and new_post_id:
            # Delete the old message (new preview was sent)
            try:
                await callback.message.delete()
            except Exception:
                pass
            logger.info(f"{mask_user_id(callback.from_user.id, config.debug_mode)} regenerated post, new_id: {new_post_id}")
        else:
            await callback.message.edit_caption(
                caption="❌ <b>Не удалось сгенерировать новый пост.</b>\n\nПопробуйте позже.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Error in cb_regenerate_post: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при регенерации", show_alert=True)


# ============================================
# CATCH-ALL CALLBACK HANDLER
# ============================================

@router.callback_query()
async def cb_unknown(callback: CallbackQuery) -> None:
    """Handle unknown callback queries."""
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)
    logger.warning(f"Unknown callback: {callback.data} from {mask_user_id(callback.from_user.id, config.debug_mode)}")
