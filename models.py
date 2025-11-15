import enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
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
        Enum(QuizScenario),
        nullable=True
    )  # сюда можно писать результат "основного" квиза

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
    dominant_scenario = Column(Enum(QuizScenario), nullable=True)

    # Статусы и тайминги
    started_at = Column(DateTime, default=func.now())
    finished_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)

    # связи
    user = relationship("User", backref="quiz_results")
    quiz = relationship("Quiz", back_populates="results")

    def __repr__(self):
        return (f"<QuizResult(user_id={self.user_id}, quiz_id={self.quiz_id}, "
                f"dominant={self.dominant_scenario})>")
