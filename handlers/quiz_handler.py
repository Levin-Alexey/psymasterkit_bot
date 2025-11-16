from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.sql import func
from database import AsyncSessionLocal
from models import User, Quiz, QuizResult, QuizScenario
from loguru import logger
from analytics import log_event

# Создаем роутер для квиза
quiz_router = Router()

# Определяем состояния FSM для квиза
class QuizStates(StatesGroup):
    question_1 = State()
    question_2 = State()
    question_3 = State()


# --- Обработчик кнопки "Начать квиз" ---
@quiz_router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as db:
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.answer("Ошибка: пользователь не найден.")
            await callback.answer()
            return
        
        # Получаем квиз
        quiz_result = await db.execute(
            select(Quiz).where(Quiz.code == "main_psych_quiz")
        )
        quiz = quiz_result.scalar_one_or_none()
        
        if not quiz:
            await callback.message.answer("Ошибка: квиз не найден в базе данных.")
            await callback.answer()
            return
        
        # Создаем запись результата квиза
        new_quiz_result = QuizResult(
            user_id=user.id,
            quiz_id=quiz.id,
            impostor_score=0,
            eternal_student_score=0,
            seeker_score=0
        )
        db.add(new_quiz_result)
        await db.commit()
        await db.refresh(new_quiz_result)
        
        # Сохраняем ID результата квиза в состоянии
        await state.update_data(quiz_result_id=new_quiz_result.id)
        
        logger.info(f"Квиз начат пользователем {user.telegram_id}, quiz_result_id={new_quiz_result.id}")
        # Логируем начало квиза
        await log_event(
            user_telegram_id=callback.from_user.id,
            event_code="quiz_started",
            payload={"quiz_result_id": new_quiz_result.id},
            quiz_code="main_psych_quiz",
        )
    
    # Отправляем первый вопрос
    question_text = "<b>Когда вы думаете о том, чтобы двигаться глубже в психологию…</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="«А вдруг я сделаю что-то не так и наврежу?»",
            callback_data="q1_impostor"
        )],
        [InlineKeyboardButton(
            text="«А вдруг это всё не про меня? А если я снова передумаю?»",
            callback_data="q1_seeker"
        )],
        [InlineKeyboardButton(
            text="«Пока не уверен(а), хочу сначала всё продумать: позиционирование, упаковка, да и клиентов бы...»",
            callback_data="q1_eternal_student"
        )]
    ])
    
    await callback.message.answer(question_text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(QuizStates.question_1)
    await callback.answer()


# --- Обработчики ответов на первый вопрос ---
@quiz_router.callback_query(F.data.startswith("q1_"), QuizStates.question_1)
async def question_1_answered(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.replace("q1_", "")
    
    # Получаем ID результата квиза из состояния
    user_data = await state.get_data()
    quiz_result_id = user_data.get("quiz_result_id")
    
    if not quiz_result_id:
        await callback.message.answer("Ошибка: не удалось найти результат квиза.")
        await callback.answer()
        return
    
    # Обновляем счетчики в базе данных
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QuizResult).where(QuizResult.id == quiz_result_id)
        )
        quiz_result = result.scalar_one_or_none()
        
        if quiz_result:
            if answer == "impostor":
                quiz_result.impostor_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 impostor (total={quiz_result.impostor_score})")
            elif answer == "seeker":
                quiz_result.seeker_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 seeker (total={quiz_result.seeker_score})")
            elif answer == "eternal_student":
                quiz_result.eternal_student_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 eternal_student (total={quiz_result.eternal_student_score})")
            
            await db.commit()
        else:
            await callback.message.answer("Ошибка: не удалось найти результат квиза.")
            await callback.answer()
            return
    
    # Отправляем второй вопрос
    question_text = "<b>Если близкий человек критикует вас, ваша реакция:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="«Оправдываюсь, спорю — и стараюсь сделать ещё лучше»",
            callback_data="q2_eternal_student"
        )],
        [InlineKeyboardButton(
            text="«Молчу, но надолго выпадаю и начинаю в себе сомневаться...»",
            callback_data="q2_seeker"
        )],
        [InlineKeyboardButton(
            text="«Чувствую укол, будто я и вправду недостаточно хорош(а)»",
            callback_data="q2_impostor"
        )]
    ])
    
    await callback.message.answer(question_text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(QuizStates.question_2)
    await callback.answer()


# --- Обработчики ответов на второй вопрос ---
@quiz_router.callback_query(F.data.startswith("q2_"), QuizStates.question_2)
async def question_2_answered(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.replace("q2_", "")
    
    # Получаем ID результата квиза из состояния
    user_data = await state.get_data()
    quiz_result_id = user_data.get("quiz_result_id")
    
    if not quiz_result_id:
        await callback.message.answer("Ошибка: не удалось найти результат квиза.")
        await callback.answer()
        return
    
    # Обновляем счетчики в базе данных
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QuizResult).where(QuizResult.id == quiz_result_id)
        )
        quiz_result = result.scalar_one_or_none()
        
        if quiz_result:
            if answer == "impostor":
                quiz_result.impostor_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 impostor (total={quiz_result.impostor_score})")
            elif answer == "seeker":
                quiz_result.seeker_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 seeker (total={quiz_result.seeker_score})")
            elif answer == "eternal_student":
                quiz_result.eternal_student_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 eternal_student (total={quiz_result.eternal_student_score})")
            
            await db.commit()
        else:
            await callback.message.answer("Ошибка: не удалось найти результат квиза.")
            await callback.answer()
            return
    
    # Отправляем третий вопрос
    question_text = "<b>Что вас больше всего тормозит?</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="«Постоянно учусь, читаю, ищу, но не могу конкретно определиться, куда идти и что делать»",
            callback_data="q3_seeker"
        )],
        [InlineKeyboardButton(
            text="«Сомневаюсь, хватит ли моих знаний, чтобы помочь другим или брать деньги»",
            callback_data="q3_impostor"
        )],
        [InlineKeyboardButton(
            text="«Хочу всё довести до идеала, прежде чем действовать»",
            callback_data="q3_eternal_student"
        )]
    ])
    
    await callback.message.answer(question_text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(QuizStates.question_3)
    await callback.answer()


# --- Обработчики ответов на третий вопрос ---
@quiz_router.callback_query(F.data.startswith("q3_"), QuizStates.question_3)
async def question_3_answered(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.replace("q3_", "")
    
    # Получаем ID результата квиза из состояния
    user_data = await state.get_data()
    quiz_result_id = user_data.get("quiz_result_id")
    
    if not quiz_result_id:
        await callback.message.answer("Ошибка: не удалось найти результат квиза.")
        await callback.answer()
        return
    
    # Обновляем счетчики в базе данных
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QuizResult).where(QuizResult.id == quiz_result_id)
        )
        quiz_result = result.scalar_one_or_none()
        
        if quiz_result:
            if answer == "impostor":
                quiz_result.impostor_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 impostor (total={quiz_result.impostor_score})")
            elif answer == "seeker":
                quiz_result.seeker_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 seeker (total={quiz_result.seeker_score})")
            elif answer == "eternal_student":
                quiz_result.eternal_student_score += 1
                logger.info(f"Quiz {quiz_result_id}: +1 eternal_student (total={quiz_result.eternal_student_score})")
            
            await db.commit()
        else:
            await callback.message.answer("Ошибка: не удалось найти результат квиза.")
            await callback.answer()
            return
    
    # Показываем кнопку для результатов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Узнать результаты сценариев",
            callback_data="show_quiz_results"
        )]
    ])
    
    await callback.message.answer("Квиз завершен!", reply_markup=keyboard)
    await callback.answer()


# --- Обработчик показа результатов квиза ---
@quiz_router.callback_query(F.data == "show_quiz_results")
async def show_quiz_results(callback: CallbackQuery, state: FSMContext):
    # Получаем ID результата квиза из состояния
    user_data = await state.get_data()
    quiz_result_id = user_data.get("quiz_result_id")
    
    if not quiz_result_id:
        await callback.message.answer("Ошибка: не удалось найти результат квиза.")
        await callback.answer()
        return
    
    # Получаем результаты из базы данных
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QuizResult).where(QuizResult.id == quiz_result_id)
        )
        quiz_result = result.scalar_one_or_none()
        
        if not quiz_result:
            await callback.message.answer("Ошибка: не удалось найти результат квиза.")
            await callback.answer()
            return
        
        # Определяем доминирующий сценарий
        scores = {
            'impostor': quiz_result.impostor_score,
            'seeker': quiz_result.seeker_score,
            'eternal_student': quiz_result.eternal_student_score
        }
        
        dominant_scenario_key = max(scores, key=scores.get)
        dominant_scenario = QuizScenario[dominant_scenario_key.upper()]
        dominant_value = dominant_scenario.value  # сохраняем строковое значение для совместимости с БД
        
        # Сохраняем доминирующий сценарий в базе (как строку, например 'impostor')
        quiz_result.dominant_scenario = dominant_value
        quiz_result.is_completed = True
        quiz_result.finished_at = func.now()
        
        # Также сохраняем в профиль пользователя
        user_result = await db.execute(
            select(User).where(User.id == quiz_result.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            # Сохраняем строковое значение в профиль пользователя
            user.main_quiz_scenario = dominant_value
        
        await db.commit()
        
        logger.info(f"Quiz {quiz_result_id} completed. Dominant scenario: {dominant_scenario_key}")
        # Логируем завершение квиза
        await log_event(
            user_telegram_id=callback.from_user.id,
            event_code="quiz_completed",
            payload={
                "quiz_result_id": quiz_result_id,
                "dominant_scenario": dominant_value,
            },
            quiz_code="main_psych_quiz",
        )
        
        # Формируем сообщение в зависимости от сценария
        if dominant_scenario == QuizScenario.IMPOSTOR:
            result_text = (
                "<b>Мы рассчитали ваш преобладающий сценарий.</b>\n"
                "Внимание — это не ярлык, а точка осознанности.\n\n"
                "🔑 Ваш сценарий — <b>«Синдром самозванца»</b>\n"
                "Вы часто чувствуете, что знаний или опыта недостаточно. "
                "Из-за этого сложно поднять цену или даже начать консультировать.\n\n"
                "✨ Дойдите до конца — и мы покажем, как перестать ждать \"ещё одного диплома\" "
                "и начать работать с тем, что уже есть.\n\n"
                "<b>На следующем этапе вы увидите, как именно ваш сценарий влияет на вашу жизнь — "
                "и почему вы теряете больше, чем кажется.</b>"
            )
        elif dominant_scenario == QuizScenario.ETERNAL_STUDENT:
            result_text = (
                "<b>Мы рассчитали ваш преобладающий сценарий.</b>\n"
                "Внимание — это не ярлык, а точка осознанности.\n\n"
                "🔑 Ваш сценарий — <b>«Вечный ученик»</b>\n"
                "Вы хотите сделать всё идеально — чтобы было «по уму», без ошибок и хаоса. "
                "Но именно это желание тормозит: вы откладываете действия, пока не будет идеального плана.\n\n"
                "✨ Дойдите до конца — и мы покажем, как выйти из паралича \"всё должно быть идеально\" "
                "и начать двигаться прямо сейчас.\n\n"
                "<b>На следующем этапе вы увидите, как именно ваш сценарий влияет на вашу жизнь — "
                "и почему вы теряете больше, чем кажется.</b>"
            )
        else:  # QuizScenario.SEEKER
            result_text = (
                "<b>Мы рассчитали ваш преобладающий сценарий.\n"
                "Внимание — это не ярлык, а точка осознанности.</b>\n\n"
                "🔑 Ваш сценарий — <b>«Искатель своего»</b>\n"
                "Вы постоянно ищете, анализируете, пробуете разные направления. "
                "Но чем больше думаете — тем труднее сделать выбор и двинуться дальше. "
                "Сомнения забирают энергию и уверенность.\n\n"
                "✨ Дойдите до конца — и мы покажем, как прекратить бесконечный поиск \"правильного пути\" "
                "и наконец сделать выбор.\n\n"
                "<b>На следующем этапе вы увидите, как именно ваш сценарий влияет на вашу жизнь — "
                "и почему вы теряете больше, чем кажется.</b>"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Хочу узнать цену своего сценария",
                callback_data="learn_scenario_cost"
            )]
        ])
        
        await callback.message.answer(result_text, parse_mode="HTML", reply_markup=keyboard)
    
    await state.clear()
    await callback.answer()

