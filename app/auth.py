import hmac
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Participant, Room
from app.utils.ids import new_session_id

AUDIENCE_COOKIE = "qa_session"
PRESENTER_QUERY = "t"


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


async def get_or_create_session_id(
    response: Response,
    qa_session: Annotated[str | None, Cookie(alias=AUDIENCE_COOKIE)] = None,
) -> str:
    if qa_session and len(qa_session) >= 16:
        return qa_session
    new = new_session_id()
    from app.config import get_settings
    is_https = get_settings().app_base_url.lower().startswith("https://")
    response.set_cookie(
        AUDIENCE_COOKIE,
        new,
        httponly=True,
        samesite="lax",
        secure=is_https,
        max_age=60 * 60 * 24 * 30,
    )
    return new


async def get_room_by_code(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> Room:
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    return room


async def require_presenter(
    request: Request,
    code: str,
    t: Annotated[str | None, Query(alias=PRESENTER_QUERY)] = None,
    session: AsyncSession = Depends(get_session),
) -> Room:
    room = await get_room_by_code(code, session)
    token = t or request.headers.get("X-Presenter-Token")
    if not token or not constant_time_eq(token, room.presenter_token):
        # No oracle: redirect to audience view rather than 401
        raise HTTPException(
            status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/r/{code}"},
        )
    return room


async def get_or_create_participant(
    room: Room,
    session_id: str,
    name: str | None,
    db: AsyncSession,
) -> Participant | None:
    result = await db.execute(
        select(Participant).where(
            Participant.room_id == room.id,
            Participant.session_id == session_id,
        )
    )
    p = result.scalar_one_or_none()
    if p is not None:
        return p
    if name is None:
        return None
    p = Participant(room_id=room.id, session_id=session_id, name=name)
    db.add(p)
    await db.flush()
    return p
