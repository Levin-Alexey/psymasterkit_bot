from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User
from pathlib import Path
from analytics import log_event

supervision_router = Router()


@supervision_router.callback_query(F.data == "learn_more_supervision")
async def handle_learn_more_supervision(callback: CallbackQuery):
    """
    Показываем подробности о "Супервизии" с разными текстами
    для психологов и непсихологов. В конце — CTA на бронь разговора.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    is_psych = bool(user and user.is_psychologist)

    if is_psych:
        text = (
            '💬 <b>Хотите из вечных сомнений выйти в уверенность и стабильный '
            'доход? Давайте проверим, подходит ли вам "Супервизия"</b>\n\n'
            'Вы только что прочитали историю Дины — от сомнений «моё ли это?» '
            'к 2-м повышениям чека и финансовой независимости.\n\n'
            'Это не случайность. Это результат системной работы над собой как '
            'экспертом.\n\n'
            '<b>На диагностическом звонке мы вместе разберём:</b>\n\n'
            '✓ Вашу текущую точку А (где вы сейчас как психолог)\n'
            '✓ Реалистичную точку Б (куда можете прийти за время Супервизии)\n'
            '✓ Подходит ли вам наш подход или лучше искать другой путь'
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text='Забронировать время разговора',
                    callback_data='book_call'
                )]
            ]
        )
        await callback.message.answer_photo(photo="https://iimg.su/i/g2zYHi")
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
    else:
        text = (
            '💫 <b>Хотите выйти из "выживания" в полноценную жизнь? Давайте '
            'проверим, поможет ли вам Супервизия</b>\n\n'
            'Вы только что прочитали историю Гузель — от одиночества и пустоты '
            'к семье, дому, путешествиям и доходу, который растёт.\n\n'
            'Это не волшебство. Это работа с собой по системе.\n'
            'Супервизия — это глубокая трансформация для тех, кто готов менять '
            'свою жизнь изнутри.\n\n'
            '<b>На диагностическом звонке мы вместе разберём:</b>\n'
            '✓ Что именно вас держит в текущей ситуации\n'
            '✓ Какие глубинные убеждения блокируют результаты\n'
            '✓ Подходит ли вам Супервизия или лучше искать другой путь'
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text='Забронировать разговор',
                    callback_data='book_call'
                )]
            ]
        )
        await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)

    await callback.answer()


@supervision_router.callback_query(F.data == 'book_call')
async def handle_book_call(callback: CallbackQuery):
    """
    После запроса на бронь разговора показываем подтверждение
    и кнопку перехода в канал.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    display_name = (user.user_name if user and user.user_name else 'Коллега')

    text = (
        f"✅ Отлично, {display_name}! Заявка отправлена.\n\n"
        "<b>Специалист свяжется с вами в течение 24 часов для подбора "
        "удобного времени.</b>\n\n"
        "А пока — приглашаю вас в отдельный канал «Супервизии» \n\n"
        "<b>Там вы найдёте:</b>\n"
        "→ Истории тех, кто уже прошёл путь от сценария к результату\n"
        "→ Полезные материалы по психологии (которые можно применять уже сейчас)\n"
        "→ Анонсы открытых эфиров с Дарьей\n"
        "→ Ответы на частые вопросы о программе"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text='Перейти в канал',
            callback_data='go_to_channel'
        )]]
    )

    await callback.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()
    # Аналитика: пользователь запросил бронь разговора (шаг 10)
    await log_event(
        user_telegram_id=callback.from_user.id,
        event_code="book_call_requested",
    )


@supervision_router.callback_query(F.data == 'go_to_channel')
async def handle_go_to_channel(callback: CallbackQuery):
    """
    Показываем кнопку для перехода в группу и отправляем подарок (файл).
    """
    url_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text='Перейти в группу',
            url='https://t.me/+9qSFHA_ryi43Y2My'
        )]]
    )
    await callback.message.answer(
        'Откройте канал по кнопке ниже:', reply_markup=url_keyboard
    )
    # Аналитика: переход в канал (шаг 11)
    await log_event(
        user_telegram_id=callback.from_user.id,
        event_code="go_to_channel_clicked",
    )

    await callback.message.answer('🎁 А теперь обещанный подарок:', parse_mode='HTML')

    # Путь к файлу относительно корня проекта
    file_path = Path(__file__).resolve().parent.parent / 'src' / 'Чек-лист реализации: от идеи до результата.pdf'
    
    # Логируем путь для диагностики
    from loguru import logger
    logger.info("Попытка отправить файл по пути: {}", file_path)
    logger.info("Файл существует: {}", file_path.exists())
    
    if file_path.exists():
        try:
            document = FSInputFile(str(file_path))
            await callback.message.answer_document(document)
            logger.info("Файл успешно отправлен пользователю {}", callback.from_user.id)
            await log_event(
                user_telegram_id=callback.from_user.id,
                event_code="gift_sent_success",
                payload={"path": str(file_path)}
            )
        except Exception as e:
            logger.error("Ошибка отправки файла: {}", e)
            await callback.message.answer(
                f'Не удалось приложить файл подарка. Ошибка: {e}'
            )
            await log_event(
                user_telegram_id=callback.from_user.id,
                event_code="gift_sent_failed",
                payload={"path": str(file_path), "error": str(e)}
            )
    else:
        logger.error("Файл не найден: {}", file_path)
        await callback.message.answer(
            f'Файл подарка не найден по пути: {file_path}'
        )
        await log_event(
            user_telegram_id=callback.from_user.id,
            event_code="gift_file_missing",
            payload={"path": str(file_path)}
        )

    await callback.answer()
