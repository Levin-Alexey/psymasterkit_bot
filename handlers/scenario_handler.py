from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User
from analytics import log_event
import aiohttp
import json
from loguru import logger

# Создаем роутер для этого обработчика
router = Router()

# URL webhook N8N
N8N_WEBHOOK_URL = "https://superegocomp.app.n8n.cloud/webhook-test/data"


# Функция отправки данных в N8N
async def send_to_n8n(user_name: str, phone: str, user_type: str):
    """
    Отправляет данные пользователя в N8N webhook.
    
    Args:
        user_name: Имя пользователя
        phone: Телефон пользователя
        user_type: 'psychologist' или 'non_psychologist'
    """
        payload = {
            "user_name": user_name,
            "phone": phone,
            "user_type": user_type,
            "telegram_username": telegram_username
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"N8N webhook успешно отправлен для {user_name} ({user_type})")
                else:
                    logger.warning(f"N8N webhook вернул статус {response.status} для {user_name}")
    except Exception as e:
        logger.error(f"Ошибка отправки в N8N webhook: {e}")


# Определяем состояния FSM
class ScenarioStates(StatesGroup):
    waiting_for_name = State()
    confirming_name = State()
    waiting_for_phone = State()
    confirming_phone = State()
    waiting_for_goal = State()

# --- 1. Обработчик нажатия на кнопку "Узнать сценарий" ---
@router.callback_query(F.data == "learn_scenario")
async def start_scenario(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Как Вас зовут?")
    await state.set_state(ScenarioStates.waiting_for_name)
    await callback.answer()

# --- 2. Обработчик получения имени ---
@router.message(ScenarioStates.waiting_for_name)
async def name_received(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Верно", callback_data="name_confirm_correct")],
        [InlineKeyboardButton(text="❌ Неверно", callback_data="name_confirm_incorrect")]
    ])
    
    await message.answer(f"Ваше имя: {message.text}. Верно?", reply_markup=keyboard)
    await state.set_state(ScenarioStates.confirming_name)

# --- 3. Обработчик подтверждения имени ("Верно") ---
@router.callback_query(F.data == "name_confirm_correct", ScenarioStates.confirming_name)
async def name_confirmed(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    user_name = user_data.get('user_name')
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user_record = result.scalar_one_or_none()
        
        if user_record:
            user_record.user_name = user_name
            await db.commit()
            # Аналитика: подтверждение имени
            await log_event(
                user_telegram_id=callback.from_user.id,
                event_code="name_confirmed",
                payload={"user_name": user_name}
            )
            await callback.message.answer(f"Отлично, {user_name}! Ваше имя сохранено.")
        else:
            await callback.message.answer("Произошла ошибка: не удалось найти ваш профиль.")
            await state.clear()
            await callback.answer()
            return
            
    await callback.message.answer("Напишите Ваш номер телефона")
    await state.set_state(ScenarioStates.waiting_for_phone)
    await callback.answer()

# --- 4. Обработчик исправления имени ("Неверно") ---
@router.callback_query(F.data == "name_confirm_incorrect", ScenarioStates.confirming_name)
async def name_incorrect(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, введите Ваше имя еще раз.")
    await state.set_state(ScenarioStates.waiting_for_name)
    await callback.answer()

# --- 5. Обработчик получения номера телефона ---
@router.message(ScenarioStates.waiting_for_phone)
async def phone_received(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Верно", callback_data="phone_confirm_correct")],
        [InlineKeyboardButton(text="❌ Неверно", callback_data="phone_confirm_incorrect")]
    ])
    
    await message.answer(f"Ваш номер: {message.text}. Верно?", reply_markup=keyboard)
    await state.set_state(ScenarioStates.confirming_phone)

# --- 6. Обработчик подтверждения телефона ("Верно") ---
@router.callback_query(F.data == "phone_confirm_correct", ScenarioStates.confirming_phone)
async def phone_confirmed(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    phone = user_data.get('phone')
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user_record = result.scalar_one_or_none()
        
        if user_record:
            user_record.phone = phone
            await db.commit()
            # Аналитика: подтверждение телефона
            await log_event(
                user_telegram_id=callback.from_user.id,
                event_code="phone_confirmed",
                payload={"phone": phone}
            )
            await callback.message.answer("Спасибо! Ваш номер телефона сохранен.")
        else:
            await callback.message.answer("Произошла ошибка: не удалось найти ваш профиль.")
            await state.clear()
            await callback.answer()
            return

    # Задаем следующий вопрос
    question_text = "Что для вас важнее прямо сейчас?"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать карьеру и получить первый доход", callback_data="goal_career")],
        [InlineKeyboardButton(text="Улучшить навыки и расширить круг клиентов", callback_data="goal_skills")],
        [InlineKeyboardButton(text="Изучать психологию для себя и саморазвития", callback_data="goal_personal")]
    ])
    
    await callback.message.answer(question_text, reply_markup=keyboard)
    await state.set_state(ScenarioStates.waiting_for_goal)
    await callback.answer()

# --- 7. Обработчик исправления телефона ("Неверно") ---
@router.callback_query(F.data == "phone_confirm_incorrect", ScenarioStates.confirming_phone)
async def phone_incorrect(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, введите Ваш номер телефона еще раз.")
    await state.set_state(ScenarioStates.waiting_for_phone)
    await callback.answer()

# --- 8. Обработчик выбора цели ---
@router.callback_query(F.data.startswith("goal_"), ScenarioStates.waiting_for_goal)
async def goal_selected(callback: CallbackQuery, state: FSMContext):
    goal = callback.data
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user_record = result.scalar_one_or_none()
        
        if user_record:
            if goal in ["goal_career", "goal_skills"]:
                user_record.is_psychologist = True
                user_record.is_not_psychologist = False
            elif goal == "goal_personal":
                user_record.is_not_psychologist = True
                user_record.is_psychologist = False
            
            await db.commit()
            # Аналитика: выбор цели
            await log_event(
                user_telegram_id=callback.from_user.id,
                event_code="goal_selected",
                payload={
                    "goal": goal,
                    "is_psychologist": bool(user_record.is_psychologist),
                    "is_not_psychologist": bool(user_record.is_not_psychologist)
                }
            )
            await callback.message.answer("Спасибо, ваш выбор сохранен!")
            
            # Отправляем следующее сообщение
            user_name = user_record.user_name or "Друг"
            next_message = (
                f"Супер, {user_name}!\n\n"
                "Вы уже сделали первый шаг в сторону своей реализации.\n\n"
                "💡 У каждого, кто выбирает этот путь - путь понимания себя, помощи другим, "
                "поиска большего масштабирования через психологию — есть свой бессознательный \"стоп\".\n\n"
                "<i>Для одного — это \"всё должно быть идеально, пока не начну\".\n"
                "Для другого — страх быть \"недостаточно обученным\".\n"
                "Третий — просто не разрешает себе брать деньги за знания.</i>\n\n"
                "Всё это — сценарии. Они работают в фоне, блокируют рост, но их можно развернуть.\n\n"
                "🎲 <b>Сейчас мы проведём небольшой разбор и покажем:\n"
                "что тормозит лично вас и как это распознать.</b>"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Узнай свой сценарий", callback_data="discover_scenario")]
            ])
            
            await callback.message.answer(next_message, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.message.answer("Произошла ошибка: не удалось найти ваш профиль.")

    await state.clear()
    await callback.answer()


# --- 9. Обработчик кнопки "Узнай свой сценарий" ---
@router.callback_query(F.data == "discover_scenario")
async def discover_scenario(callback: CallbackQuery, state: FSMContext):
    # Получаем данные пользователя из БД для отправки в N8N
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.user_name and user.phone:
            # Определяем тип пользователя
            user_type = "psychologist" if user.is_psychologist else "non_psychologist"
            
            # Отправляем данные в N8N
                await send_to_n8n(
                    user_name=user.user_name,
                    phone=user.phone,
                    user_type=user_type,
                    telegram_username=user.telegram_username
                )
    
    message_text = (
        "✨ <b>Пора заглянуть глубже.</b>\n\n"
        "Ни образование, ни опыт, ни даже харизма не играют ключевой роли, "
        "если внутри работает ограничивающий сценарий.\n\n"
        "Этот сценарий может звучать как логичный страх, как «ещё не время» "
        "или как «пока не готов(а)»\n\n"
        "Но он делает одно: <b>останавливает.</b>\n\n"
        "💬 <b>Хотите узнать, что именно вас держит, мешает реализоваться по-настоящему — "
        "хоть вы уже в теме психологии, хоть только начинаете путь?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать квиз", callback_data="start_quiz")]
    ])
    
    await callback.message.answer(message_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

