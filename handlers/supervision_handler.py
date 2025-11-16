from aiogram import Router, F
from aiogram.types import CallbackQuery

supervision_router = Router()


@supervision_router.callback_query(F.data == "learn_more_supervision")
async def handle_learn_more_supervision(callback: CallbackQuery):
    """
    Временный обработчик. Здесь позже покажем детали о программе "Супервизия".
    """
    await callback.message.answer(
        "Скоро здесь появится подробная информация о программе «Супервизия».",
        parse_mode="HTML",
    )
    await callback.answer()
