import pytest
from pydantic import ValidationError

from app.schemas import (
    JoinRequest,
    QuestionCreateRequest,
    QuestionPatchRequest,
    RoomCreateRequest,
)


def test_room_create_strips_blank_title_to_none():
    req = RoomCreateRequest(title="   ")
    assert req.title is None


def test_room_create_accepts_email():
    req = RoomCreateRequest(title="Hi", presenter_email="a@b.co")
    assert req.presenter_email == "a@b.co"


def test_room_create_rejects_bad_email():
    with pytest.raises(ValidationError):
        RoomCreateRequest(presenter_email="not-an-email")


def test_join_rejects_blank_name():
    with pytest.raises(ValidationError):
        JoinRequest(name="   ")


def test_question_rejects_oversize():
    with pytest.raises(ValidationError):
        QuestionCreateRequest(text="x" * 281)


def test_question_strips_whitespace():
    req = QuestionCreateRequest(text="  hello  ")
    assert req.text == "hello"


def test_patch_accepts_state_only():
    p = QuestionPatchRequest(state="pinned")
    assert p.state == "pinned"
    assert p.starred is None


def test_patch_rejects_invalid_state():
    with pytest.raises(ValidationError):
        QuestionPatchRequest(state="bogus")
