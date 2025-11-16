from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, Quiz, NonPsychQuizResult
from analytics import log_event

non_psych_cost_router = Router()


# FSM состояния для квиза
class NonPsychQuizStates(StatesGroup):
    waiting_q1_months = State()
    waiting_q2_frequency = State()
    waiting_q3_sabotage = State()


# Маппинг callback → значения
MONTHS_MAP = {
    "q1_6m": 6,
    "q1_1y": 12,
    "q1_2y": 24,
    "q1_2y_plus": 36,
}

FREQUENCY_COEF_MAP = {
    "q2_rare": 1,
    "q2_few_month": 2,
    "q2_weekly": 4,
    "q2_daily": 8,
}

# Список возможных пунктов саботажа для вопроса 3
SABOTAGE_OPTIONS = [
    ("q3_books", "Читала книги / смотрела лекции / проходила мини-курсы"),
    ("q3_help_people", "Думала: «Могла бы помогать людям, но не решаюсь»"),
    ("q3_analysis", "Анализировала себя, близких, ситуации — но это оставалось «в голове»"),
    ("q3_stuck", "Чувствовала застревание: учусь, но не двигаюсь"),
    ("q3_postpone", "Откладывала реальные шаги, потому что «ещё не готова»"),
    ("q3_search", "Искала «правильное направление», но так и не выбрала"),
]


@non_psych_cost_router.callback_query(F.data == "calc_scenario_cost_non_psych")
async def calc_scenario_cost_non_psych(callback: CallbackQuery, state: FSMContext):
    """
    Старт квиза для НЕ психологов: упущенный потенциал.
    """
    logger.info(
        "Пользователь {} начал квиз упущенного потенциала (не психолог)",
        callback.from_user.id,
    )

    # Вопрос 1: сколько времени интересуется психологией
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 6 месяцев", callback_data="q1_6m")],
        [InlineKeyboardButton(text="1 год", callback_data="q1_1y")],
        [InlineKeyboardButton(text="2 года", callback_data="q1_2y")],
        [InlineKeyboardButton(text="Больше 2 лет", callback_data="q1_2y_plus")],
    ])

    await callback.message.answer(
        "<b>Вопрос 1 из 3</b>\n\n"
        "Сколько времени вы уже интересуетесь психологией?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await state.set_state(NonPsychQuizStates.waiting_q1_months)
    await callback.answer()
    # Событие: старт квиза не-психолога
    await log_event(
        user_telegram_id=callback.from_user.id,
        event_code="non_psych_quiz_started",
        quiz_code="non_psych_quiz_1",
    )


@non_psych_cost_router.callback_query(
    NonPsychQuizStates.waiting_q1_months,
    F.data.in_(MONTHS_MAP.keys())
)
async def process_q1_months(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос 1: месяцы в психологии."""
    months = MONTHS_MAP[callback.data]
    await state.update_data(months_in_psychology=months)

    logger.info(
        "Пользователь {} выбрал {} месяцев в психологии",
        callback.from_user.id,
        months,
    )

    # Вопрос 2: как часто возникает мысль
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Раз в месяц или реже",
            callback_data="q2_rare"
        )],
        [InlineKeyboardButton(
            text="Несколько раз в месяц",
            callback_data="q2_few_month"
        )],
        [InlineKeyboardButton(
            text="Примерно раз в неделю",
            callback_data="q2_weekly"
        )],
        [InlineKeyboardButton(
            text="Почти каждый день",
            callback_data="q2_daily"
        )],
    ])

    await callback.message.answer(
        "<b>Вопрос 2 из 3</b>\n\n"
        "Как часто у вас возникает мысль:\n"
        "<i>«Хочу начать что-то делать с этим, но пока не знаю как/"
        "не готова/не время»</i>?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await state.set_state(NonPsychQuizStates.waiting_q2_frequency)
    await callback.answer()


@non_psych_cost_router.callback_query(
    NonPsychQuizStates.waiting_q2_frequency,
    F.data.in_(FREQUENCY_COEF_MAP.keys())
)
async def process_q2_frequency(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос 2: частота мыслей."""
    coef = FREQUENCY_COEF_MAP[callback.data]
    await state.update_data(frequency_coef=coef)

    logger.info(
        "Пользователь {} выбрал коэффициент частоты {}",
        callback.from_user.id,
        coef,
    )

    # Вопрос 3: чекбоксы саботажа (можно несколько)
    buttons = []
    for code, text in SABOTAGE_OPTIONS:
        buttons.append([InlineKeyboardButton(text=text, callback_data=code)])

    # Кнопка завершения выбора
    buttons.append([InlineKeyboardButton(
        text="✅ Готово, перейти к результатам",
        callback_data="q3_done"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Сохраняем пустой список выбранных пунктов
    await state.update_data(sabotage_codes=[])

    await callback.message.answer(
        "<b>Вопрос 3 из 3</b>\n\n"
        "Что из этого вы уже делали или чувствовали?\n"
        "<i>(можно выбрать несколько, затем нажать «Готово»)</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await state.set_state(NonPsychQuizStates.waiting_q3_sabotage)
    await callback.answer()


@non_psych_cost_router.callback_query(
    NonPsychQuizStates.waiting_q3_sabotage,
    F.data.startswith("q3_")
)
async def process_q3_sabotage(callback: CallbackQuery, state: FSMContext):
    """
    Обработка вопроса 3: чекбоксы саботажа.
    Можно выбрать несколько. callback_data = 'q3_done' — завершение.
    """
    data = await state.get_data()
    sabotage_codes = data.get("sabotage_codes", [])

    if callback.data == "q3_done":
        # Завершение выбора — переходим к подсчёту
        logger.info(
            "Пользователь {} завершил выбор саботажа, выбрано: {}",
            callback.from_user.id,
            len(sabotage_codes),
        )
        await show_non_psych_result(callback, state)
        return

    # Иначе — это один из вариантов q3_...
    # Добавляем/убираем из списка (тогл)
    if callback.data in sabotage_codes:
        sabotage_codes.remove(callback.data)
        action = "снят"
    else:
        sabotage_codes.append(callback.data)
        action = "выбран"

    await state.update_data(sabotage_codes=sabotage_codes)

    logger.info(
        "Пользователь {} {} пункт {}, всего выбрано: {}",
        callback.from_user.id,
        action,
        callback.data,
        len(sabotage_codes),
    )

    # Уведомление пользователя
    await callback.answer(
        f"Выбрано: {len(sabotage_codes)}",
        show_alert=False
    )


async def show_non_psych_result(callback: CallbackQuery, state: FSMContext):
    """
    Подсчёт и отображение результата квиза для не-психолога.
    Сохранение в БД, затем переход в общий CTA.
    """
    data = await state.get_data()
    months = data.get("months_in_psychology", 12)
    coef = data.get("frequency_coef", 1)
    sabotage_codes = data.get("sabotage_codes", [])

    # Расчёты
    days_in_psychology = round(months * 365 / 12)
    thoughts_count = months * coef
    sabotage_items_count = len(sabotage_codes)
    sabotage_forms_total = 4 + sabotage_items_count

    logger.info(
        "Подсчёт результата: months={}, coef={}, sabotage_count={}, "
        "days={}, thoughts={}",
        months,
        coef,
        sabotage_items_count,
        days_in_psychology,
        thoughts_count,
    )

    # Сохранение в БД
    async with AsyncSessionLocal() as db:
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback.message.answer(
                "Ошибка: пользователь не найден в базе данных."
            )
            await state.clear()
            return

        # Получаем квиз (или создаём)
        quiz_code = "non_psych_quiz_1"
        result = await db.execute(
            select(Quiz).where(Quiz.code == quiz_code)
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            quiz = Quiz(
                code=quiz_code,
                title="Квиз упущенного потенциала (не-психолог)",
                is_active=True,
            )
            db.add(quiz)
            await db.commit()
            await db.refresh(quiz)

        # Создаём запись результата
        quiz_result = NonPsychQuizResult(
            user_id=user.id,
            quiz_id=quiz.id,
            is_psychologist_snapshot=False,
            months_in_psychology=months,
            frequency_coef=coef,
            sabotage_items_count=sabotage_items_count,
            sabotage_items_codes=",".join(sabotage_codes) if sabotage_codes else None,
            days_in_psychology=days_in_psychology,
            thoughts_count=thoughts_count,
            sabotage_forms_total=sabotage_forms_total,
        )
        db.add(quiz_result)
        await db.commit()

        logger.info(
            "Результат квиза сохранён для пользователя {}: "
            "days={}, thoughts={}, sabotage_forms={}",
            user.telegram_id,
            days_in_psychology,
            thoughts_count,
            sabotage_forms_total,
        )

    # Получаем имя пользователя
    user_name = callback.from_user.first_name or "Друг"

    # Формируем сообщение с результатом
    result_text = (
        f"<b>{user_name}, вот что получилось:</b>\n\n"
        f"✦ Вы прожили <b>{days_in_psychology} дней</b> в поле психологии — "
        f"но без выхода в реальную практику\n\n"
        f"✦ <b>{thoughts_count} раз</b> возвращались к мысли о действии — "
        f"но откладывали его\n\n"
        f"✦ Накопили <b>{sabotage_forms_total} форм</b> саботажа, "
        f"которые держат вас в подвешенном состоянии\n\n"
        f"<b>А теперь представьте:</b>\n\n"
        f"Что если бы год назад вы начали не читать ещё одну книгу, "
        f"а применять то, что уже знаете — к себе, своей жизни, своим отношениям?\n\n"
        f"<b>Сейчас у вас было бы:</b>\n\n"
        f"✅ 12 месяцев реальной практики — вы бы разобрали свои триггеры, "
        f"паттерны, сценарии\n\n"
        f"✅ Понимание, что работает именно для вас — не в теории, а на опыте\n\n"
        f"✅ Навык поддерживать себя и близких — осознанно, а не интуитивно\n\n"
        f"✅ Внутреннее спокойствие вместо мысли "
        f"«когда же я наконец начну что-то с этим делать»"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Хочу начать действовать",
            callback_data="no_more_scenario"
        )]
    ])

    await callback.message.answer(
        result_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await state.clear()
    await callback.answer()
    # Событие: завершение квиза не-психолога
    await log_event(
        user_telegram_id=callback.from_user.id,
        event_code="non_psych_quiz_completed",
        payload={
            "months": months,
            "coef": coef,
            "sabotage_forms_total": sabotage_forms_total,
        },
        quiz_code="non_psych_quiz_1",
    )

