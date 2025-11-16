
from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, QuizScenario, ScenarioCostResult, Quiz

# Создаем роутер для обработчика цены сценария
scenario_cost_router = Router()

# Состояния FSM для опроса о стоимости
class CostQuizStates(StatesGroup):
    waiting_income_expected = State()
    waiting_income_current = State()
    waiting_months_delay = State()

SCENARIO_RU_NAMES = {
    QuizScenario.IMPOSTOR: "Синдром самозванца",
    QuizScenario.ETERNAL_STUDENT: "Вечный ученик",
    QuizScenario.SEEKER: "Искатель своего"
}

# Маппинг ответов на числовые значения
EXPECTED_INCOME_MAP = {
    "price_q1_50k": 50_000,
    "price_q1_100k": 100_000,
    "price_q1_200k": 200_000,
}

CURRENT_INCOME_MAP = {
    "price_q2_0": 0,
    "price_q2_5_30": 30_000,  # берем верхнюю границу
    "price_q2_30_70": 70_000,
    "price_q2_70_plus": 100_000,  # условно для расчета
}

MONTHS_DELAY_MAP = {
    "price_q3_3": 3,
    "price_q3_6": 6,
    "price_q3_9": 9,
    "price_q3_12": 12,
}


async def calculate_scenario_cost(
    telegram_id: int,
    expected_income: int,
    current_income: int,
    months_delay: int,
) -> ScenarioCostResult | None:
    """
    Функция расчета стоимости сценария для психологов.
    Сохраняет результат в базу данных и возвращает его.
    """
    async with AsyncSessionLocal() as db:
        # Получаем пользователя
        user_result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_psychologist:
            logger.warning(
                f"Пользователь {telegram_id} не найден или не психолог"
            )
            return None
        
        # Получаем квиз
        quiz_result = await db.execute(
            select(Quiz).where(Quiz.code == "main_psych_quiz")
        )
        quiz = quiz_result.scalar_one_or_none()
        
        if not quiz:
            logger.error("Квиз main_psych_quiz не найден в базе данных")
            return None
        
        # Расчет
        lost_per_month = max(expected_income - current_income, 0)
        lost_total = lost_per_month * months_delay
        lost_3_years = lost_per_month * 36
        
        # Создание записи
        cost_result = ScenarioCostResult(
            user_id=user.id,
            quiz_id=quiz.id,
            is_psychologist_snapshot=True,
            scenario=user.main_quiz_scenario,
            expected_income=expected_income,
            current_income=current_income,
            months_delay=months_delay,
            lost_per_month=lost_per_month,
            lost_total=lost_total,
            lost_3_years=lost_3_years,
        )
        
        db.add(cost_result)
        await db.commit()
        await db.refresh(cost_result)
        
        logger.info(
            f"Сохранен результат расчета для пользователя {telegram_id}: "
            f"lost_total={lost_total}, lost_3_years={lost_3_years}"
        )
        
        return cost_result


async def show_cost_results(callback: CallbackQuery, cost_result: ScenarioCostResult):
    """
    Показывает персонализированное сообщение с результатами расчета.
    """
    async with AsyncSessionLocal() as db:
        # Получаем пользователя для имени
        user_result = await db.execute(
            select(User).where(User.id == cost_result.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await callback.message.answer("Ошибка: пользователь не найден.")
            return
        
        user_name = user.user_name or "Пользователь"
        scenario_ru = SCENARIO_RU_NAMES.get(
            cost_result.scenario, "[не определён]"
        )
        
        # Форматируем числа
        expected = f"{cost_result.expected_income:,}".replace(",", " ")
        current = f"{cost_result.current_income:,}".replace(",", " ")
        lost_per_month = f"{cost_result.lost_per_month:,}".replace(",", " ")
        lost_total = f"{cost_result.lost_total:,}".replace(",", " ")
        lost_3_years = f"{cost_result.lost_3_years:,}".replace(",", " ")
        
        result_text = (
            f"📊 {user_name}, смотрите:\n\n"
            f"→ Вы хотите зарабатывать {expected} ₽ в месяц, "
            f"а пока получаете {current} ₽.\n"
            f"→ Это минус {lost_per_month} ₽ ежемесячно.\n\n"
            f"За {cost_result.months_delay} месяцев сценарий «{scenario_ru}» "
            f"уже обошелся вам примерно в {lost_total} ₽.\n\n"
            "Давайте остановимся на секунду:\n\n"
            f"Если ничего не изменить — через 3 года эта цифра станет "
            f"{lost_3_years} ₽.\n\n"
            "Деньги, которые могли быть у вас на счёте.\n"
            "Свобода, которую вы могли получить.\n"
            "Жизнь, которую откладываете \"на потом\"\n\n"
            f"Вы правда хотите отдать сценарию «{scenario_ru}» ещё один год?"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Нет, не хочу",
                    callback_data="no_more_scenario"
                )]
            ]
        )
        
        await callback.message.answer(
            result_text, parse_mode="HTML", reply_markup=keyboard
        )


@scenario_cost_router.callback_query(F.data == "no_more_scenario")
async def no_more_scenario(callback: CallbackQuery):
    """
    Обработчик кнопки "Нет, не хочу" - финальное сообщение.
    """
    logger.info(f"Пользователь {callback.from_user.id} завершил расчет стоимости")
    
    await callback.message.answer(
        "Отлично! Это первый шаг к изменениям. "
        "Скоро мы свяжемся с вами для дальнейших действий."
    )
    await callback.answer()

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


@scenario_cost_router.callback_query(F.data == "calc_scenario_cost")
async def calc_scenario_cost(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Посчитать реальную цену моего сценария'.
    Запускает серию из трех вопросов.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} начал расчет стоимости сценария"
    )

    # Первый вопрос
    question_text = (
        "<b>Сколько, по вашим ощущениям, вы могли бы зарабатывать "
        "как психолог (в месяц)?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="50 000 ₽",
                callback_data="price_q1_50k"
            )],
            [InlineKeyboardButton(
                text="100 000 ₽",
                callback_data="price_q1_100k"
            )],
            [InlineKeyboardButton(
                text="200 000 ₽+",
                callback_data="price_q1_200k"
            )]
        ]
    )
    
    await callback.message.answer(
        question_text, parse_mode="HTML", reply_markup=keyboard
    )
    await state.set_state(CostQuizStates.waiting_income_expected)
    await callback.answer()


@scenario_cost_router.callback_query(
    F.data.startswith("price_q1_"), CostQuizStates.waiting_income_expected
)
async def question_1_answered(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик ответа на первый вопрос о желаемом доходе.
    """
    expected_income = EXPECTED_INCOME_MAP.get(callback.data)
    
    if not expected_income:
        await callback.message.answer("Ошибка: некорректный ответ.")
        await callback.answer()
        return
    
    # Сохраняем ответ в состоянии
    await state.update_data(expected_income=expected_income)
    
    logger.info(
        f"Пользователь {callback.from_user.id} выбрал желаемый доход: {expected_income}"
    )
    
    # Второй вопрос
    question_text = (
        "<b>А сколько сейчас вы реально получаете именно от психологии?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="0 ₽ (ещё не консультирую)",
                callback_data="price_q2_0"
            )],
            [InlineKeyboardButton(
                text="5–30 000 ₽",
                callback_data="price_q2_5_30"
            )],
            [InlineKeyboardButton(
                text="30–70 000 ₽",
                callback_data="price_q2_30_70"
            )],
            [InlineKeyboardButton(
                text="Больше 70 000 ₽",
                callback_data="price_q2_70_plus"
            )]
        ]
    )
    
    await callback.message.answer(
        question_text, parse_mode="HTML", reply_markup=keyboard
    )
    await state.set_state(CostQuizStates.waiting_income_current)
    await callback.answer()


@scenario_cost_router.callback_query(
    F.data.startswith("price_q2_"), CostQuizStates.waiting_income_current
)
async def question_2_answered(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик ответа на второй вопрос о текущем доходе.
    """
    current_income = CURRENT_INCOME_MAP.get(callback.data)
    
    if current_income is None:
        await callback.message.answer("Ошибка: некорректный ответ.")
        await callback.answer()
        return
    
    # Сохраняем ответ в состоянии
    await state.update_data(current_income=current_income)
    
    logger.info(
        f"Пользователь {callback.from_user.id} выбрал текущий доход: "
        f"{current_income}"
    )
    
    # Третий вопрос
    question_text = (
        "<b>Сколько месяцев вы уже откладываете старт (или рост)?</b>"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="3 месяца",
                callback_data="price_q3_3"
            )],
            [InlineKeyboardButton(
                text="6 месяцев",
                callback_data="price_q3_6"
            )],
            [InlineKeyboardButton(
                text="9 месяцев",
                callback_data="price_q3_9"
            )],
            [InlineKeyboardButton(
                text="12 месяцев",
                callback_data="price_q3_12"
            )]
        ]
    )
    
    await callback.message.answer(
        question_text, parse_mode="HTML", reply_markup=keyboard
    )
    await state.set_state(CostQuizStates.waiting_months_delay)
    await callback.answer()


@scenario_cost_router.callback_query(
    F.data.startswith("price_q3_"), CostQuizStates.waiting_months_delay
)
async def question_3_answered(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик ответа на третий вопрос о месяцах задержки.
    Запускает расчет и показ результатов.
    """
    months_delay = MONTHS_DELAY_MAP.get(callback.data)
    
    if not months_delay:
        await callback.message.answer("Ошибка: некорректный ответ.")
        await callback.answer()
        return
    
    # Получаем все ответы из состояния
    user_data = await state.get_data()
    expected_income = user_data.get("expected_income")
    current_income = user_data.get("current_income")
    
    if not expected_income or current_income is None:
        await callback.message.answer("Ошибка: не все ответы сохранены.")
        await callback.answer()
        return
    
    logger.info(
        f"Пользователь {callback.from_user.id} завершил опрос: "
        f"expected={expected_income}, current={current_income}, "
        f"months={months_delay}"
    )
    
    # Вызываем функцию расчета и сохранения
    cost_result = await calculate_scenario_cost(
        callback.from_user.id,
        expected_income,
        current_income,
        months_delay
    )
    
    if not cost_result:
        await callback.message.answer(
            "Ошибка: не удалось рассчитать стоимость сценария."
        )
        await callback.answer()
        return
    
    # Показываем результаты
    await show_cost_results(callback, cost_result)
    await state.clear()
    await callback.answer()
