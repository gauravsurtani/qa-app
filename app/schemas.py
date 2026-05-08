from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


NameStr = Annotated[str, Field(min_length=1, max_length=40)]
QuestionText = Annotated[str, Field(min_length=1, max_length=280)]
TitleStr = Annotated[str, Field(min_length=1, max_length=80)]


class RoomCreateRequest(BaseModel):
    title: TitleStr | None = None
    presenter_email: EmailStr | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None
        return v


class RoomCreateResponse(BaseModel):
    code: str
    presenter_url: str
    audience_url: str


class JoinRequest(BaseModel):
    name: NameStr

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class QuestionCreateRequest(BaseModel):
    text: QuestionText

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class QuestionPatchRequest(BaseModel):
    state: Literal["live", "pinned", "answered", "hidden"] | None = None
    starred: bool | None = None


class QuestionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_name: str
    text: str
    state: str
    starred: bool
    upvote_count: int
    created_at: datetime


class RoomStateDTO(BaseModel):
    code: str
    title: str | None
    status: str
    questions: list[QuestionDTO]
    my_upvotes: list[int]
    my_question_ids: list[int]
    participant_count: int
