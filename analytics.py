from typing import Optional, Dict, Any
from sqlalchemy import select
from database import AsyncSessionLocal
from models import UserEvent, User, Quiz
from loguru import logger


async def log_event(user_telegram_id: int, event_code: str, payload: Optional[Dict[str, Any]] = None, quiz_code: Optional[str] = None) -> None:
    """
    Логирование пользовательского события в таблицу user_events.
    Можно передать quiz_code, чтобы связать событие с конкретным квизом.
    """
    async with AsyncSessionLocal() as db:
        # Найдём пользователя по telegram_id
        result = await db.execute(select(User).where(User.telegram_id == user_telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("log_event: пользователь с tg={} не найден", user_telegram_id)
            return

        quiz_id = None
        if quiz_code:
            qres = await db.execute(select(Quiz).where(Quiz.code == quiz_code))
            quiz = qres.scalar_one_or_none()
            if quiz:
                quiz_id = quiz.id

        event = UserEvent(
            user_id=user.id,
            quiz_id=quiz_id,
            event_code=event_code,
            payload=payload or {},
        )
        db.add(event)
        await db.commit()
        logger.info("Записано событие {} для пользователя {}", event_code, user_telegram_id)
