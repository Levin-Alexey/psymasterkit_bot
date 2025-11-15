
from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from loguru import logger
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, QuizScenario

# Создаем роутер для обработчика цены сценария
scenario_cost_router = Router()

SCENARIO_RU_NAMES = {
    QuizScenario.IMPOSTOR: "Синдром самозванца",
    QuizScenario.ETERNAL_STUDENT: "Вечный ученик",
    QuizScenario.SEEKER: "Искатель своего"
}

@scenario_cost_router.callback_query(F.data == "learn_scenario_cost")
async def learn_scenario_cost(callback: CallbackQuery):
    """
    Обработчик для всех трех сценариев после завершения квиза.
    Показывает информацию о цене/последствиях текущего сценария пользователя.
    """

    logger.info(
        f"Пользователь {callback.from_user.id} нажал 'Узнать цену сценария'"
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await callback.message.answer("Ошибка: пользователь не найден.")
        await callback.answer()
        return

    # Ветка для психологов
    if user.is_psychologist:
        scenario = user.main_quiz_scenario
        scenario_ru = SCENARIO_RU_NAMES.get(scenario, "[не определён]")
        user_name = user.user_name or "Пользователь"

        msg = (
            f"{user_name}, вы узнали свой блокирующий сценарий: "
            f"<b>\"{scenario_ru}\".</b>\n\n"
            "Возможно, это было неожиданно. Или, наоборот, вы думали: 'Да, это про меня...'\n\n"
            "Предлагаю посмотреть глубже: <b>Давайте честно посчитаем, во сколько этот сценарий вам обходится.</b>\n\n"
            "Не в абстрактных понятиях, а в конкретных рублях."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Посчитать реальную цену моего сценария",
                    callback_data="calc_scenario_cost"
                )]
            ]
        )
        await callback.message.answer(
            msg, parse_mode="HTML", reply_markup=keyboard
        )
        await callback.answer()
        return

    # TODO: Ветка для не психологов (user.is_not_psychologist)
    await callback.message.answer(
        "Здесь будет информация о том, как ваш сценарий влияет на вашу жизнь "
        "и почему вы теряете больше, чем кажется."
    )
    await callback.answer()
