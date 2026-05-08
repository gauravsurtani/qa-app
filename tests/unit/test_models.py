from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.models import Participant, Question, QuestionState, Room, RoomStatus, Upvote


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


async def test_create_room_with_defaults(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)
    assert room.id is not None
    assert room.status == RoomStatus.ACTIVE
    assert room.closed_at is None
    assert room.email_sent_at is None


async def test_question_with_participant(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.flush()
    p = Participant(room_id=room.id, session_id="s1", name="Sam")
    session.add(p)
    await session.flush()
    q = Question(room_id=room.id, participant_id=p.id, author_name="Sam", text="Hi")
    session.add(q)
    await session.commit()
    await session.refresh(q)
    assert q.state == QuestionState.LIVE
    assert q.starred is False
    assert q.upvote_count == 0


async def test_upvote_composite_pk_prevents_dupes(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.flush()
    p = Participant(room_id=room.id, session_id="s1", name="Sam")
    session.add(p)
    await session.flush()
    q = Question(room_id=room.id, participant_id=p.id, author_name="Sam", text="Hi")
    session.add(q)
    await session.flush()

    session.add(Upvote(question_id=q.id, participant_id=p.id))
    await session.commit()

    session.add(Upvote(question_id=q.id, participant_id=p.id))
    with pytest.raises(Exception):
        await session.commit()
