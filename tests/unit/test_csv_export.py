from datetime import UTC, datetime

from app.models import Question, QuestionState, Room, RoomStatus
from app.services.csv_export import build_csv


def test_build_csv_includes_bom_and_header():
    room = Room(
        id=1,
        code="ABCDEF",
        presenter_token="t" * 32,
        title="Hi",
        status=RoomStatus.ACTIVE,
        expires_at=datetime.now(UTC),
    )
    payload = build_csv(room, [])
    text = payload.decode("utf-8")
    assert text.startswith("﻿")
    assert "question_id,author_name,text,state,starred,upvote_count" in text


def test_build_csv_writes_rows():
    room = Room(
        id=1,
        code="ABCDEF",
        presenter_token="t" * 32,
        title="Hi",
        status=RoomStatus.ACTIVE,
        expires_at=datetime.now(UTC),
    )
    q = Question(
        id=10,
        room_id=1,
        participant_id=1,
        author_name="Sam",
        text="hello",
        state=QuestionState.LIVE,
        starred=False,
        upvote_count=3,
        created_at=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
    )
    payload = build_csv(room, [q]).decode("utf-8")
    assert "Sam" in payload
    assert "hello" in payload
    assert "ABCDEF" in payload
