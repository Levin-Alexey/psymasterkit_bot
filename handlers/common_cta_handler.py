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
    is_psychologist = False
    if user:
        scenario = user.main_quiz_scenario
        is_psychologist = bool(user.is_psychologist)
        if isinstance(scenario, str):
            try:
                scenario = QuizScenario(scenario)
            except Exception:
                scenario = None

    scenario_ru = SCENARIO_RU_NAMES.get(scenario, "ваш сценарий")

    if is_psychologist:
        text = (
            "<b>Сегодня вечером — важное видео для вас</b> 🎥\n\n"
            "Вы узнаете:\n"
            f"→ Почему сценарий «{scenario_ru}» так сильно тормозит ваше развитие\n"
            "→ Где именно вы теряете энергию и уверенность\n"
            "→ Что делать прямо сейчас, чтобы сдвинуться с мёртвой точки"
        )
    else:
        text = (
            "<b>Сегодня вечером — важное видео для вас</b> 🎥\n\n"
            "В нём мы покажем:\n"
            "→ Как выйти из цикла \"интересуюсь психологией, но ничего не делаю\"\n"
            f"→ Что нужно изменить в первую очередь, чтобы сценарий «{scenario_ru}» отпустил\n"
            "→ И как начать применять знания на практике — без страха и бесконечной подготовки"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Хочу получить видео", callback_data="get_video")]
        ]
    )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@common_cta_router.callback_query(F.data == "get_video")
async def handle_get_video(callback: CallbackQuery):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    user_name = None
    if user:
        user_name = user.user_name

    display_name = user_name or "Коллега"

    text = (
        f"<b>{display_name}, вы прошли два ключевых шага:</b>\n\n"
        "✓ Узнали свой блокирующий сценарий\n"
        "✓ Посчитали, во сколько он вам обходится\n\n"
        "Теперь у вас есть полная картина происходящего, вы видите проблему и понимаете её масштаб.\n\n"
        "Пришло время для самого важного — показать вам выход из этой ловушки."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Узнать, как изменить сценарий",
                callback_data="learn_how_to_change"
            )]
        ]
    )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@common_cta_router.callback_query(F.data == "learn_how_to_change")
async def handle_learn_how_to_change(callback: CallbackQuery):
    text = (
        "Вот видео с разбором, как изменить сценарий."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Смотреть видео",
                    url="https://ya.ru"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Готов(а) к следующему шагу",
                    callback_data="ready_for_next_step"
                )
            ]
        ]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()