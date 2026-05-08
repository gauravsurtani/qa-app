from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question, QuestionState

ALLOWED_STATES: set[str] = {s.value for s in QuestionState}


class InvalidStateTransition(ValueError):
    pass


async def set_question_state(
    db: AsyncSession,
    *,
    room_id: int,
    question: Question,
    new_state: str,
) -> None:
    if new_state not in ALLOWED_STATES:
        raise InvalidStateTransition(f"Unknown state: {new_state}")
    if new_state == QuestionState.PINNED.value:
        await db.execute(
            update(Question)
            .where(
                Question.room_id == room_id,
                Question.state == QuestionState.PINNED.value,
                Question.id != question.id,
            )
            .values(state=QuestionState.LIVE.value)
        )
    question.state = QuestionState(new_state)
    await db.flush()


async def set_question_starred(
    db: AsyncSession,
    *,
    question: Question,
    starred: bool,
) -> None:
    question.starred = starred
    await db.flush()
