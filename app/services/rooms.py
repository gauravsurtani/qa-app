from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Room, RoomStatus
from app.utils.codes import generate_room_code
from app.utils.ids import new_presenter_token


def _new_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=get_settings().room_ttl_hours)


async def create_room(
    db: AsyncSession,
    *,
    title: str | None,
    presenter_email: str | None,
    max_attempts: int = 5,
) -> Room:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        room = Room(
            code=generate_room_code(),
            presenter_token=new_presenter_token(),
            title=title,
            presenter_email=presenter_email,
            status=RoomStatus.ACTIVE,
            expires_at=_new_expiry(),
        )
        db.add(room)
        try:
            await db.commit()
            await db.refresh(room)
            return room
        except IntegrityError as e:
            await db.rollback()
            last_error = e
    assert last_error is not None
    raise last_error


async def touch_room(db: AsyncSession, room: Room) -> None:
    from datetime import datetime

    room.last_activity_at = datetime.now(UTC)
    room.expires_at = _new_expiry()
    await db.flush()


async def close_room(db: AsyncSession, room: Room) -> None:
    from datetime import datetime

    now = datetime.now(UTC)
    room.status = RoomStatus.CLOSED
    room.closed_at = now
    room.last_activity_at = now
    room.expires_at = now + timedelta(hours=get_settings().room_ttl_hours)
    await db.flush()


async def expired_rooms(db: AsyncSession) -> Iterable[Room]:
    from datetime import datetime

    now = datetime.now(UTC)
    result = await db.execute(select(Room).where(Room.expires_at < now))
    return result.scalars().all()
