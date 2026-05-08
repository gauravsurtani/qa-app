from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_presenter
from app.config import get_settings
from app.db import get_session
from app.models import Participant, Question, Room
from app.schemas import RoomCreateRequest, RoomCreateResponse
from app.services.csv_export import build_csv
from app.services.email import send_session_ended_email
from app.services.pubsub import pubsub
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
    background_tasks: BackgroundTasks,
    room: Room = Depends(require_presenter),
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if room.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Room already closed")
    await close_room(db, room)
    await db.commit()

    await pubsub.publish(
        room.id,
        {"type": "room.closed", "data": {"reason": "presenter_ended"}},
    )

    if room.presenter_email and room.email_sent_at is None:
        result = await db.execute(
            select(Question).where(Question.room_id == room.id).order_by(Question.created_at)
        )
        questions = list(result.scalars())
        total_upvotes = sum(q.upvote_count for q in questions)
        p_count = await db.scalar(
            select(func.count()).select_from(Participant).where(Participant.room_id == room.id)
        )
        csv_bytes = build_csv(room, questions)

        title = room.title
        permalink = f"{get_settings().app_base_url.rstrip('/')}/r/{room.code}"
        html_body = _render_email_html(
            title=title,
            stats={"total": len(questions), "upvotes": total_upvotes, "participants": p_count or 0},
            permalink=permalink,
        )
        filename = f"qa-{room.code}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"
        room_id = room.id
        to_address = room.presenter_email
        subject = f"Your Q&A session '{title or room.code}' has ended"

        async def _send_and_record():
            ok = await send_session_ended_email(
                to_address=to_address,
                subject=subject,
                html_body=html_body,
                csv_attachment=csv_bytes,
                csv_filename=filename,
            )
            if ok:
                from app.db import get_sessionmaker
                sm = get_sessionmaker()
                async with sm() as s:
                    fresh = await s.get(Room, room_id)
                    if fresh:
                        fresh.email_sent_at = datetime.now(timezone.utc)
                        await s.commit()

        background_tasks.add_task(_send_and_record)

    return {"status": "closed"}


def _render_email_html(*, title: str | None, stats: dict, permalink: str) -> str:
    env = Environment(
        loader=FileSystemLoader(Path(__file__).resolve().parent.parent.parent / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("email/session_ended.html").render(
        title=title, stats=stats, permalink=permalink,
    )
