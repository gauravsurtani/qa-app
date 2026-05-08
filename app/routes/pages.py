from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_or_create_session_id, get_room_by_code
from app.db import get_session
from app.models import Participant, Question, QuestionState, RoomStatus, Upvote

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(request, "home.html", {})


@router.get("/r/{code}", response_class=HTMLResponse)
async def audience_view(
    code: str,
    request: Request,
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
):
    room = await get_room_by_code(code, db)
    if room.status == RoomStatus.CLOSED:
        return request.app.state.templates.TemplateResponse(
            request, "room_ended.html", {"room": room}
        )

    p_result = await db.execute(
        select(Participant).where(
            Participant.room_id == room.id,
            Participant.session_id == session_id,
        )
    )
    participant = p_result.scalar_one_or_none()
    needs_join = participant is None

    questions: list = []
    my_upvotes: list[int] = []
    my_question_ids: list[int] = []
    if not needs_join:
        q_result = await db.execute(
            select(Question)
            .where(
                Question.room_id == room.id,
                Question.state.in_([QuestionState.LIVE, QuestionState.PINNED, QuestionState.ANSWERED]),
            )
            .order_by(Question.upvote_count.desc(), Question.created_at.desc())
        )
        questions = q_result.scalars().all()

        u_result = await db.execute(
            select(Upvote.question_id).where(Upvote.participant_id == participant.id)
        )
        my_upvotes = [r[0] for r in u_result.all()]
        my_question_ids = [q.id for q in questions if q.participant_id == participant.id]

    return request.app.state.templates.TemplateResponse(
        request,
        "audience.html",
        {
            "room": room,
            "participant": participant,
            "needs_join": needs_join,
            "questions": questions,
            "my_upvotes": my_upvotes,
            "my_question_ids": my_question_ids,
        },
    )
