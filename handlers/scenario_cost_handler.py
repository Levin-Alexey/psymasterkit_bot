from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

# Создаем роутер для обработчика цены сценария
scenario_cost_router = Router()


# --- Обработчик кнопки "Хочу узнать цену своего сценария" ---
@scenario_cost_router.callback_query(F.data == "learn_scenario_cost")
async def learn_scenario_cost(callback: CallbackQuery):
    """
    Обработчик для всех трех сценариев после завершения квиза.
    Показывает информацию о цене/последствиях текущего сценария пользователя.
    """
    logger.info(f"Пользователь {callback.from_user.id} нажал 'Узнать цену сценария'")
    
    # TODO: Здесь будет логика показа информации о цене сценария
    await callback.message.answer(
        "Здесь будет информация о том, как ваш сценарий влияет на вашу жизнь "
        "и почему вы теряете больше, чем кажется."
    )
    
    await callback.answer()
