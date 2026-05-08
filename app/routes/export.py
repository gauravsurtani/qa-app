from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_presenter
from app.db import get_session
from app.models import Question, Room
from app.services.csv_export import build_csv

router = APIRouter()


@router.get("/r/{code}/export.csv")
async def export_csv(
    code: str,
    room: Room = Depends(require_presenter),
    db: AsyncSession = Depends(get_session),
) -> Response:
    result = await db.execute(
        select(Question).where(Question.room_id == room.id).order_by(Question.created_at.asc())
    )
    questions = list(result.scalars())
    payload = build_csv(room, questions)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"qa-{room.code}-{today}.csv"
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
