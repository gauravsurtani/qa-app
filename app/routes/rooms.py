from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_presenter
from app.config import get_settings
from app.db import get_session
from app.models import Room
from app.schemas import RoomCreateRequest, RoomCreateResponse
from app.services.rooms import close_room, create_room

router = APIRouter()


@router.post("/rooms", response_model=RoomCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_room_endpoint(
    body: RoomCreateRequest,
    db: AsyncSession = Depends(get_session),
) -> RoomCreateResponse:
    room = await create_room(
        db,
        title=body.title,
        presenter_email=str(body.presenter_email) if body.presenter_email else None,
    )
    base = get_settings().app_base_url.rstrip("/")
    return RoomCreateResponse(
        code=room.code,
        presenter_url=f"{base}/r/{room.code}/host?t={room.presenter_token}",
        audience_url=f"{base}/r/{room.code}",
    )


@router.post("/r/{code}/end")
async def end_session(
    response: Response,
    room: Room = Depends(require_presenter),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if room.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Room already closed")
    await close_room(db, room)
    await db.commit()
    return {"status": "closed"}
