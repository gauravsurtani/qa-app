from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.models import Participant, Question, QuestionState, Room
from app.services.questions import (
    InvalidStateTransition,
    set_question_starred,
    set_question_state,
)


@pytest_asyncio.fixture
async def session_with_room():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        room = Room(
            code="ACDEFG",
            presenter_token="t" * 32,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        s.add(room)
        await s.flush()
        p = Participant(room_id=room.id, session_id="s1", name="A")
        s.add(p)
        await s.flush()
        yield s, room, p
    await engine.dispose()


async def test_pin_unpins_others(session_with_room):
    s, room, p = session_with_room
    q1 = Question(room_id=room.id, participant_id=p.id, author_name="A", text="1")
    q2 = Question(room_id=room.id, participant_id=p.id, author_name="A", text="2")
    s.add_all([q1, q2])
    await s.flush()

    await set_question_state(s, room_id=room.id, question=q1, new_state="pinned")
    await s.flush()
    await set_question_state(s, room_id=room.id, question=q2, new_state="pinned")
    await s.commit()

    refreshed = await s.execute(
        select(Question).where(Question.room_id == room.id).order_by(Question.id)
    )
    states = [q.state for q in refreshed.scalars()]
    assert states == [QuestionState.LIVE, QuestionState.PINNED]


async def test_invalid_state_raises(session_with_room):
    s, room, p = session_with_room
    q = Question(room_id=room.id, participant_id=p.id, author_name="A", text="x")
    s.add(q)
    await s.flush()
    import pytest
    with pytest.raises(InvalidStateTransition):
        await set_question_state(s, room_id=room.id, question=q, new_state="bogus")


async def test_star_is_orthogonal(session_with_room):
    s, room, p = session_with_room
    q = Question(room_id=room.id, participant_id=p.id, author_name="A", text="x")
    s.add(q)
    await s.flush()
    await set_question_starred(s, question=q, starred=True)
    assert q.starred is True
    await set_question_state(s, room_id=room.id, question=q, new_state="answered")
    assert q.starred is True  # unchanged
    assert q.state == QuestionState.ANSWERED
