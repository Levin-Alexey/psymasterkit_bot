from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, QuizScenario

common_cta_router = Router()

SCENARIO_RU_NAMES = {
    QuizScenario.IMPOSTOR: "Синдром самозванца",
    QuizScenario.ETERNAL_STUDENT: "Вечный ученик",
    QuizScenario.SEEKER: "Искатель своего",
}


@common_cta_router.callback_query(F.data == "no_more_scenario")
async def handle_no_more_scenario(callback: CallbackQuery):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    scenario = None
    if user:
        scenario = user.main_quiz_scenario
        if isinstance(scenario, str):
            try:
                scenario = QuizScenario(scenario)
            except Exception:
                scenario = None

    scenario_ru = SCENARIO_RU_NAMES.get(scenario, "ваш сценарий")

    text = (
        "<b>Сегодня вечером — важное видео для вас</b> 🎥\n\n"
        "Вы узнаете:\n"
        f"→ Почему сценарий «{scenario_ru}» так сильно тормозит ваше развитие\n"
        "→  Где именно вы теряете энергию и уверенность\n"
        "→  Что делать прямо сейчас, чтобы сдвинуться с мёртвой точки\n\n"
        "Кнопка: Хочу получить видео"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Хочу получить видео", callback_data="get_video")]
        ]
    )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()