from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.auth import constant_time_eq, get_or_create_session_id, get_room_by_code
from app.config import get_settings
from app.db import get_session
from app.models import Participant, Question, QuestionState, RoomStatus, Upvote
from app.utils.codes import is_valid_room_code
from app.utils.qr import generate_qr_svg

router = APIRouter()


def _audience_url(code: str) -> str:
    base = get_settings().app_base_url.rstrip("/")
    return f"{base}/{code}"


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> Response:
    return request.app.state.templates.TemplateResponse(request, "home.html", {})


async def _render_audience_view(
    code: str,
    request: Request,
    session_id: str,
    db: AsyncSession,
) -> Response:
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

    questions: list[Question] = []
    my_upvotes: list[int] = []
    my_question_ids: list[int] = []
    if not needs_join and participant is not None:
        q_result = await db.execute(
            select(Question)
            .where(
                Question.room_id == room.id,
                Question.state.in_(
                    [QuestionState.LIVE, QuestionState.PINNED, QuestionState.ANSWERED]
                ),
            )
            .order_by(Question.upvote_count.desc(), Question.created_at.desc())
        )
        questions = list(q_result.scalars().all())

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


@router.get("/r/{code}", response_class=HTMLResponse)
async def audience_view(
    code: str,
    request: Request,
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> Response:
    return await _render_audience_view(code, request, session_id, db)


@router.get("/r/{code}/host", response_class=HTMLResponse)
async def presenter_view(
    code: str,
    request: Request,
    t: str | None = None,
    v: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> Response:
    room = await get_room_by_code(code, db)
    if not t or not constant_time_eq(t, room.presenter_token):
        return RedirectResponse(f"/{code}", status_code=303)

    audience_url = _audience_url(room.code)

    q_result = await db.execute(
        select(Question)
        .where(Question.room_id == room.id)
        .order_by(Question.upvote_count.desc(), Question.created_at.desc())
    )
    questions = q_result.scalars().all()

    if not questions and v != "live":
        return request.app.state.templates.TemplateResponse(
            request,
            "presenter_share.html",
            {
                "room": room,
                "token": t,
                "audience_url": audience_url,
                "qr_svg": generate_qr_svg(audience_url),
            },
        )

    return request.app.state.templates.TemplateResponse(
        request,
        "presenter.html",
        {"room": room, "token": t, "questions": questions},
    )


@router.get("/r/{code}/host/qr", response_class=HTMLResponse)
async def fullscreen_qr(
    code: str,
    request: Request,
    t: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> Response:
    room = await get_room_by_code(code, db)
    if not t or not constant_time_eq(t, room.presenter_token):
        return RedirectResponse(f"/{code}", status_code=303)
    audience_url = _audience_url(room.code)
    return request.app.state.templates.TemplateResponse(
        request,
        "fullscreen_qr.html",
        {
            "room": room,
            "audience_url": audience_url,
            "qr_svg": generate_qr_svg(audience_url, scale=14),
        },
    )


# Catch-all short audience URL: /{code}. Registered last so explicit routes
# (/, /r/..., /healthz, /rooms, /static/...) all match first. The handler itself
# 404s anything that doesn't pass `is_valid_room_code` so /favicon.ico and friends
# still 404 cleanly instead of querying the DB.
@router.get("/{code}", response_class=HTMLResponse)
async def short_audience_view(
    code: str,
    request: Request,
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> Response:
    if not is_valid_room_code(code):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return await _render_audience_view(code, request, session_id, db)
