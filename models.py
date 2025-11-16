import enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class QuizScenario(enum.Enum):
    IMPOSTOR = "impostor"            # Синдром самозванца
    ETERNAL_STUDENT = "eternal_student"  # Вечный ученик
    SEEKER = "seeker"                # Искатель своего


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    user_name = Column(String)
    phone = Column(String)
    bot_start_datetime = Column(DateTime, default=func.now())
    is_psychologist = Column(Boolean, default=False)
    is_not_psychologist = Column(Boolean, default=False)

    # --- признак пользователя по главному квизу ---
    main_quiz_scenario = Column(
        Enum(
            QuizScenario,
            name="quizscenario",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )  # сюда можно писать результат "основного" квиза

    # Связи с каскадным удалением
    quiz_results = relationship(
        "QuizResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    scenario_cost_results = relationship(
        "ScenarioCostResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    non_psych_quiz_results = relationship(
        "NonPsychQuizResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, user_name='{self.user_name}')>"


class Quiz(Base):
    __tablename__ = 'quizzes'

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)  # 'psych_quiz_1', 'psych_quiz_2' и т.п.
    title = Column(String, nullable=False)              # Человекочитаемое название
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # связь: quiz.results
    results = relationship("QuizResult", back_populates="quiz")

    def __repr__(self):
        return f"<Quiz(code='{self.code}', title='{self.title}')>"


class QuizResult(Base):
    __tablename__ = 'quiz_results'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)

    # Счётчики по сценариям
    impostor_score = Column(Integer, default=0)          # Синдром самозванца
    eternal_student_score = Column(Integer, default=0)   # Вечный ученик
    seeker_score = Column(Integer, default=0)            # Искатель своего

    # Итоговый сценарий по этому квизу
    dominant_scenario = Column(
        Enum(
            QuizScenario,
            name="quizscenario",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )

    # Статусы и тайминги
    started_at = Column(DateTime, default=func.now())
    finished_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)

    # связи
    user = relationship("User", back_populates="quiz_results")
    quiz = relationship("Quiz", back_populates="results")

    def __repr__(self):
        return (f"<QuizResult(user_id={self.user_id}, quiz_id={self.quiz_id}, "
                f"dominant={self.dominant_scenario})>")


class ScenarioCostResult(Base):
    __tablename__ = 'scenario_cost_results'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)

    # снимок статуса — записываем только для психологов
    is_psychologist_snapshot = Column(Boolean, default=True, nullable=False)

    # сценарий из первого квиза (IMPOSTOR / ETERNAL_STUDENT / SEEKER)
    scenario = Column(
        Enum(
            QuizScenario,
            name="quizscenario",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )

    # Ответы пользователя
    expected_income = Column(Integer, nullable=False)  # желаемый доход / мес
    current_income = Column(Integer, nullable=False)   # текущий доход / мес
    months_delay = Column(Integer, nullable=False)     # сколько месяцев откладывает

    # Расчётные значения
    lost_per_month = Column(Integer, nullable=False)   # упущено в месяц
    lost_total = Column(Integer, nullable=False)       # упущено за период (months_delay)
    lost_3_years = Column(Integer, nullable=False)     # прогноз за 3 года

    created_at = Column(DateTime, default=func.now())

    # связи
    user = relationship("User", back_populates="scenario_cost_results")
    quiz = relationship("Quiz")

    def __repr__(self):
        return (
            f"<ScenarioCostResult(user_id={self.user_id}, "
            f"expected={self.expected_income}, current={self.current_income}, "
            f"months={self.months_delay}, lost_total={self.lost_total})>"
        )


class UserEvent(Base):
    __tablename__ = 'user_events'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=True)

    # Короткий код события: 'bot_start', 'name_confirmed', 'quiz_started', ...
    event_code = Column(String, nullable=False)

    # Доп. данные события (произвольные ключи), хранится как JSONB
    payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # связи
    user = relationship("User", backref="events")
    quiz = relationship("Quiz")

    def __repr__(self):
        return (
            f"<UserEvent(user_id={self.user_id}, code={self.event_code}, quiz_id={self.quiz_id})>"
        )

class NonPsychQuizResult(Base):
    """
    Результаты квиза для НЕ психологов:
    - сколько времени интересуется психологией
    - как часто думает "хочу что-то делать, но откладываю"
    - сколько пунктов саботажа выбрал(а)
    """

    __tablename__ = 'non_psych_quiz_results'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'), nullable=False)

    # снимок статуса — здесь ожидаем, что user.is_psychologist == False
    is_psychologist_snapshot = Column(Boolean, default=False, nullable=False)

    # ----- СЫРЫЕ ОТВЕТЫ -----

    # Вопрос 1: сколько времени интересуется психологией (в месяцах)
    # До 6 месяцев  -> 6
    # 1 год         -> 12
    # 2 года        -> 24
    # Больше 2 лет  -> 36
    months_in_psychology = Column(Integer, nullable=False)

    # Вопрос 2: как часто возникает мысль «хочу начать, но откладываю»
    # 1 = раз в месяц или реже
    # 2 = несколько раз в месяц
    # 4 = примерно раз в неделю
    # 8 = почти каждый день
    frequency_coef = Column(Integer, nullable=False)

    # Вопрос 3: сколько пунктов из списка выбрал(а)
    sabotage_items_count = Column(Integer, nullable=False)

    # (опционально) коды выбранных пунктов, через запятую:
    # например: "books,help_people,analysis,stuck,postpone,search_direction"
    sabotage_items_codes = Column(String, nullable=True)

    # ----- РАСЧЁТНЫЕ ПОЛЯ -----

    # пример для 24 месяцев: ~730 дней
    days_in_psychology = Column(Integer, nullable=False)

    # сколько раз возвращался(ась) к мысли о действии
    # пример: 24 месяца * coef=4 => 96 раз
    thoughts_count = Column(Integer, nullable=False)

    # "накопили {4 + количество выбранных} формы саботажа"
    sabotage_forms_total = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=func.now())

    # связи
    user = relationship("User", back_populates="non_psych_quiz_results")
    quiz = relationship("Quiz")

    def __repr__(self):
        return (
            f"<NonPsychQuizResult(user_id={self.user_id}, "
            f"months={self.months_in_psychology}, "
            f"coef={self.frequency_coef}, "
            f"sabotage_count={self.sabotage_items_count})>"
        )
