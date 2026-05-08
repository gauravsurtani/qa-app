from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    get_or_create_participant,
    get_or_create_session_id,
    get_room_by_code,
)
from app.config import get_settings
from app.db import get_session
from app.models import Question, Upvote
from app.routes.questions import _ensure_room_writable
from app.services.pubsub import pubsub
from app.services.ratelimit import RateLimiter

router = APIRouter()

_upvote_limiter: RateLimiter | None = None


def get_upvote_limiter() -> RateLimiter:
    global _upvote_limiter
    if _upvote_limiter is None:
        s = get_settings()
        _upvote_limiter = RateLimiter(max_actions=s.rate_limit_upvotes_per_min, window_seconds=60)
    return _upvote_limiter


@router.post("/r/{code}/questions/{qid}/upvote")
async def upvote(
    code: str,
    qid: int,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    db: AsyncSession = Depends(get_session),
) -> dict[str, int | bool]:
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)
    p = await get_or_create_participant(room, session_id, None, db)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Join the room first")

    rl = get_upvote_limiter()
    if not rl.allow(f"{room.id}:{p.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Slow down a sec")

    q = await db.get(Question, qid)
    if q is None or q.room_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    existing = await db.execute(
        select(Upvote).where(Upvote.question_id == qid, Upvote.participant_id == p.id)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        q.upvote_count = max(0, q.upvote_count - 1)
        upvoted = False
    else:
        try:
            db.add(Upvote(question_id=qid, participant_id=p.id))
            q.upvote_count += 1
            upvoted = True
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return {"upvotes": q.upvote_count, "upvoted": True}

    await db.commit()
    await pubsub.publish(
        room.id,
        {"type": "question.upvoted", "data": {"id": q.id, "upvotes": q.upvote_count}},
    )
    return {"upvotes": q.upvote_count, "upvoted": upvoted}
