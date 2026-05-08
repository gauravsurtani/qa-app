from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RoomStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class QuestionState(StrEnum):
    LIVE = "live"
    PINNED = "pinned"
    ANSWERED = "answered"
    HIDDEN = "hidden"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    presenter_token: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    presenter_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    status: Mapped[RoomStatus] = mapped_column(String(16), default=RoomStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    session_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(40))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    room: Mapped[Room] = relationship(back_populates="participants")
    questions: Mapped[list["Question"]] = relationship(back_populates="participant")
    upvotes: Mapped[list["Upvote"]] = relationship(back_populates="participant")

    __table_args__ = (
        UniqueConstraint("room_id", "session_id", name="uq_participants_room_session"),
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"))
    author_name: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    state: Mapped[QuestionState] = mapped_column(String(16), default=QuestionState.LIVE)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    upvote_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    room: Mapped[Room] = relationship(back_populates="questions")
    participant: Mapped[Participant] = relationship(back_populates="questions")
    upvotes: Mapped[list["Upvote"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_questions_room_state_score",
            "room_id",
            "state",
            "upvote_count",
            "created_at",
        ),
    )


class Upvote(Base):
    __tablename__ = "upvotes"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    question: Mapped[Question] = relationship(back_populates="upvotes")
    participant: Mapped[Participant] = relationship(back_populates="upvotes")
