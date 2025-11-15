import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
from loguru import logger
from database import init_db, AsyncSessionLocal
from models import User
from sqlalchemy import select
from handlers import scenario_handler
from handlers.quiz_handler import quiz_router
from handlers.scenario_cost_handler import scenario_cost_router

# Загрузка переменных окружения
load_dotenv()

# Инициализация FSM storage
# Для продакшена рекомендуется использовать более персистентное хранилище, например Redis
storage = MemoryStorage()

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher(storage=storage)

# Включаем роутеры
dp.include_router(scenario_handler.router)
dp.include_router(quiz_router)
dp.include_router(scenario_cost_router)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start. Сохраняет пользователя в базу данных."""
    async with AsyncSessionLocal() as db:
        # Проверяем, существует ли пользователь
        result = await db.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            # Создаем нового пользователя
            new_user = User(
                telegram_id=message.from_user.id,
                user_name=message.from_user.username
            )
            db.add(new_user)
            await db.commit()
            logger.info(f"Новый пользователь {message.from_user.id} ({message.from_user.username}) добавлен в базу данных.")
        else:
            logger.info(f"Пользователь {message.from_user.id} ({message.from_user.username}) уже существует в базе данных.")

    start_text = (
        "<b>А вы знали, что 93% людей, которые чувствуют тягу к психологии, так и не реализуют этот потенциал полностью?</b>\n\n"
        "Причина — в трех токсичных внутренних сценариях, которые блокируют наш потенциал на разных уровнях:\n\n"
        "✅ когда мы только увлекаемся психологией\n"
        "✅ когда начинаем практиковать\n"
        "✅ когда активно работаем с клиентами\n\n"
        "🎭 Эти сценарии работают незаметно. Они звучат как:\n\n"
        '<i>"Мне ещё учиться и учиться"</i>\n'
        '<i>"Я недостаточно опытен для этого"</i>\n'
        '<i>"Сейчас не то время, вот когда..."</i>\n'
        '<i>"У меня нет сил/энергии/ресурса"</i>\n\n'
        "Звучит как здравый смысл, но это ловушка — внутренняя программа, которая откладывает вашу реализацию снова и снова.\n\n"
        "<b>Хотите узнать, какой именно сценарий сейчас сдерживает ваш рост, вашу реализацию и ваш переход к стабильности?</b>\n\n"
        '<i>А ещё - получить чек-лист "Пошаговая схема реализации цели", который поможет развернуть этот сценарий?</i>'
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Узнать сценарий", callback_data="learn_scenario")]
    ])
    
    await message.answer(start_text, parse_mode="HTML", reply_markup=keyboard)
    logger.info(f"Пользователь {message.from_user.id} запустил бота")


async def main():
    """Главная функция запуска бота"""
    await init_db()
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
