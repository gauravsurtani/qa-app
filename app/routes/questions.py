from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AUDIENCE_COOKIE,
    get_or_create_participant,
    get_or_create_session_id,
    get_room_by_code,
    require_presenter,
)
from app.config import get_settings
from app.db import get_session
from app.models import Question, QuestionState, Room, RoomStatus
from app.schemas import (
    JoinRequest,
    QuestionCreateRequest,
    QuestionDTO,
    QuestionPatchRequest,
)
from app.services.questions import set_question_starred, set_question_state
from app.services.ratelimit import RateLimiter
from app.services.rooms import touch_room

router = APIRouter()

_question_limiter: RateLimiter | None = None


def get_question_limiter() -> RateLimiter:
    global _question_limiter
    if _question_limiter is None:
        s = get_settings()
        _question_limiter = RateLimiter(
            max_actions=s.rate_limit_questions_per_min, window_seconds=60
        )
    return _question_limiter


def _ensure_room_writable(room: Room) -> None:
    if room.status == RoomStatus.CLOSED:
        raise HTTPException(status.HTTP_410_GONE, "Room is closed")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires = room.expires_at.replace(tzinfo=None) if room.expires_at.tzinfo else room.expires_at
    if expires < now:
        raise HTTPException(status.HTTP_410_GONE, "Room is expired")


@router.post("/r/{code}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_room(
    code: str,
    body: JoinRequest,
    response: Response,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    db: AsyncSession = Depends(get_session),
):
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)
    p = await get_or_create_participant(room, session_id, body.name, db)
    if p is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not create participant")
    p.name = body.name
    await db.commit()
    response.status_code = 204
    return response


@router.post("/r/{code}/questions", response_model=QuestionDTO, status_code=201)
async def create_question(
    code: str,
    body: QuestionCreateRequest,
    response: Response,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    qa_session: Annotated[str | None, Cookie(alias=AUDIENCE_COOKIE)] = None,
    db: AsyncSession = Depends(get_session),
) -> QuestionDTO:
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)

    p = await get_or_create_participant(room, session_id, None, db)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Join the room first")

    rl = get_question_limiter()
    if not rl.allow(f"{room.id}:{p.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Slow down a sec")

    q = Question(
        room_id=room.id,
        participant_id=p.id,
        author_name=p.name,
        text=body.text,
    )
    db.add(q)
    await touch_room(db, room)
    await db.commit()
    await db.refresh(q)
    return QuestionDTO.model_validate(q)


@router.patch("/r/{code}/questions/{qid}", response_model=QuestionDTO)
async def patch_question(
    code: str,
    qid: int,
    body: QuestionPatchRequest,
    room: Room = Depends(require_presenter),
    db: AsyncSession = Depends(get_session),
) -> QuestionDTO:
    q = await db.get(Question, qid)
    if q is None or q.room_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    if body.state is not None:
        await set_question_state(db, room_id=room.id, question=q, new_state=body.state)
    if body.starred is not None:
        await set_question_starred(db, question=q, starred=body.starred)

    await touch_room(db, room)
    await db.commit()
    await db.refresh(q)
    return QuestionDTO.model_validate(q)
