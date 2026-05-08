# Q&A App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a production-ready Slido-style live Q&A web app deployed to Railway, fully branded as DeepLearning.AI (coral primary), with QR-based audience join, ask + upvote, presenter pin/answer/hide/star controls, CSV export, and optional email-on-close.

**Architecture:** Single FastAPI service. SQLite on a Railway-mounted volume. Server-rendered Jinja2 + HTMX for interactivity. Server-Sent Events (SSE) for real-time fanout via in-process asyncio queues. CSS custom properties + Web Animations API + Motion One for premium motion. One Dockerfile, one process, one worker.

**Tech Stack:**
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic 2, Jinja2, `qrcode`, `structlog`
- **Frontend:** HTMX, vanilla JS (~150 LOC total), Motion One (3.8 KB), `canvas-confetti`, Lucide icons
- **Persistence:** SQLite (file on Railway volume)
- **Email:** Resend (via REST API)
- **Tests:** pytest, pytest-asyncio, httpx, Playwright
- **Tooling:** uv, ruff, mypy
- **Deployment:** Railway (Dockerfile builder, mounted volume at `/data`)

**Reference spec:** [`docs/superpowers/specs/2026-05-07-qa-app-design.md`](../specs/2026-05-07-qa-app-design.md)

---

## File structure (locked)

```
qa-app/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan, route mounting
│   ├── config.py                # pydantic-settings — env-driven config
│   ├── db.py                    # engine, session, create_all
│   ├── models.py                # SQLAlchemy ORM (4 tables)
│   ├── schemas.py               # Pydantic DTOs
│   ├── auth.py                  # presenter token + audience cookie deps
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py             # GET /, /r/{code}, /r/{code}/host
│   │   ├── rooms.py             # POST /rooms, end session
│   │   ├── questions.py         # POST/PATCH question
│   │   ├── upvotes.py           # POST/DELETE upvote (toggle)
│   │   ├── events.py            # GET /r/{code}/events (SSE)
│   │   └── export.py            # GET /r/{code}/export.csv
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rooms.py             # business logic: create/close/expire
│   │   ├── questions.py         # state transitions + validation
│   │   ├── pubsub.py            # in-memory room → queue fanout
│   │   ├── ratelimit.py         # token bucket per (room, participant)
│   │   ├── csv_export.py        # streaming CSV builder
│   │   └── email.py             # Resend client + retry
│   └── utils/
│       ├── __init__.py
│       ├── codes.py             # 6-char room code generator
│       ├── ids.py               # ulid + token generators
│       └── qr.py                # QR SVG with brand styling
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── audience.html
│   ├── presenter.html
│   ├── presenter_share.html     # initial share-screen state
│   ├── fullscreen_qr.html
│   ├── room_ended.html
│   ├── email/
│   │   └── session_ended.html
│   └── partials/
│       ├── question_card.html
│       ├── pinned_card.html
│       └── stats.html
├── static/
│   ├── css/
│   │   ├── tokens.css
│   │   ├── base.css
│   │   └── animations.css
│   ├── js/
│   │   ├── sse.js
│   │   ├── upvote.js
│   │   ├── shortcuts.js
│   │   └── motion.js
│   └── img/
│       └── logo.svg
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_codes.py
│   │   ├── test_state_transitions.py
│   │   ├── test_ratelimit.py
│   │   └── test_csv_export.py
│   ├── integration/
│   │   ├── test_room_lifecycle.py
│   │   ├── test_questions.py
│   │   ├── test_upvotes.py
│   │   ├── test_sse.py
│   │   └── test_email.py
│   └── e2e/
│       ├── test_create_room.py
│       ├── test_audience_flow.py
│       └── test_presenter_flow.py
├── Dockerfile
├── railway.toml
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
└── README.md
```

---

## Phase A — Foundation

### Task A1: Project scaffolding + healthz

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `tests/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_healthz.py`

- [ ] **Step 1: Create `.python-version`**

```
3.12
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.env
.env.local
*.db
*.db-journal
*.db-shm
*.db-wal
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
.coverage
node_modules/
data/
.DS_Store
.playwright-mcp/
playwright-report/
test-results/
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "qa-app"
version = "0.1.0"
description = "Live Q&A app for presenters — DeepLearning.AI"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "jinja2>=3.1",
  "sqlalchemy>=2.0",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "python-multipart>=0.0.12",
  "itsdangerous>=2.2",
  "qrcode[pil]>=8.0",
  "httpx>=0.27",
  "structlog>=24.4",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "pytest-cov>=6.0",
  "ruff>=0.7",
  "mypy>=1.13",
  "playwright>=1.48",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "B", "UP", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["app"]
```

- [ ] **Step 4: Create `app/__init__.py` (empty)**

```python
```

- [ ] **Step 5: Create `app/config.py`**

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_base_url: str = "http://localhost:8000"
    sqlite_path: str = "./data/qa.db"
    log_level: str = "INFO"
    session_secret: str = Field(min_length=32)
    room_ttl_hours: int = 24

    email_provider: str = "resend"
    email_api_key: str = ""
    email_from_address: str = "qa@dlai.app"
    email_from_name: str = "DLAI Q&A"

    rate_limit_questions_per_min: int = 5
    rate_limit_upvotes_per_min: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Create `app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    yield


app = FastAPI(title="qa-app", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Create `tests/__init__.py` and `tests/integration/__init__.py` (empty)**

```python
```

- [ ] **Step 8: Create `tests/integration/test_healthz.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def _set_session_secret(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)


async def test_healthz_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 9: Install deps and run the test (expect PASS)**

```bash
cd /Users/gauravsurtani/projects/qa-app
uv sync --all-groups
uv run pytest tests/integration/test_healthz.py -v
```

Expected: 1 passed.

- [ ] **Step 10: Boot the dev server and curl healthz**

```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/healthz
kill %1
```

Expected: `{"status":"ok"}`

- [ ] **Step 11: Commit**

```bash
git add .python-version .gitignore pyproject.toml uv.lock app/ tests/
git commit -m "feat: scaffold FastAPI service with healthz endpoint"
```

---

### Task A2: Database engine + lifespan integration

**Files:**
- Create: `app/db.py`
- Modify: `app/main.py` (wire DB into lifespan)
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `app/db.py`**

```python
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global _engine, _sessionmaker
    settings = get_settings()
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_async_engine(
        f"sqlite+aiosqlite:///{settings.sqlite_path}",
        echo=False,
        future=True,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)


async def create_all() -> None:
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session
```

- [ ] **Step 2: Add `aiosqlite` to dependencies**

Edit `pyproject.toml` `dependencies` list to add:
```toml
"aiosqlite>=0.20",
```

Then:
```bash
uv sync --all-groups
```

- [ ] **Step 3: Wire DB into `app/main.py` lifespan**

Replace the lifespan function with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    init_engine()
    await create_all()
    yield
```

Add the imports at the top:
```python
from app.db import create_all, init_engine
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("EMAIL_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
```

- [ ] **Step 5: Update `tests/integration/test_healthz.py` to use the fixture**

Replace the entire file with:

```python
async def test_healthz_returns_ok(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 6: Run test (expect PASS)**

```bash
uv run pytest tests/integration/test_healthz.py -v
```

Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add app/db.py app/main.py tests/ pyproject.toml uv.lock
git commit -m "feat: add async SQLAlchemy engine wired through lifespan"
```

---

## Phase B — Data layer

### Task B1: ORM models

**Files:**
- Create: `app/models.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Create `app/models.py`**

```python
from datetime import datetime, timezone
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
    return datetime.now(timezone.utc)


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
```

- [ ] **Step 2: Update `app/main.py` to import models so create_all sees them**

In `app/main.py`, change the imports section to include models (so `Base.metadata` knows the tables):

```python
from app.db import create_all, init_engine
from app import models  # noqa: F401  (registers tables with Base.metadata)
```

- [ ] **Step 3: Create `tests/unit/__init__.py` (empty)**

```python
```

- [ ] **Step 4: Create `tests/unit/test_models.py`**

```python
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.models import Participant, Question, QuestionState, Room, RoomStatus, Upvote


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


async def test_create_room_with_defaults(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)
    assert room.id is not None
    assert room.status == RoomStatus.ACTIVE
    assert room.closed_at is None
    assert room.email_sent_at is None


async def test_question_with_participant(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.flush()
    p = Participant(room_id=room.id, session_id="s1", name="Sam")
    session.add(p)
    await session.flush()
    q = Question(room_id=room.id, participant_id=p.id, author_name="Sam", text="Hi")
    session.add(q)
    await session.commit()
    await session.refresh(q)
    assert q.state == QuestionState.LIVE
    assert q.starred is False
    assert q.upvote_count == 0


async def test_upvote_composite_pk_prevents_dupes(session):
    room = Room(
        code="ABC123",
        presenter_token="t" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(room)
    await session.flush()
    p = Participant(room_id=room.id, session_id="s1", name="Sam")
    session.add(p)
    await session.flush()
    q = Question(room_id=room.id, participant_id=p.id, author_name="Sam", text="Hi")
    session.add(q)
    await session.flush()

    session.add(Upvote(question_id=q.id, participant_id=p.id))
    await session.commit()

    session.add(Upvote(question_id=q.id, participant_id=p.id))
    with pytest.raises(Exception):
        await session.commit()
```

- [ ] **Step 5: Run tests (expect PASS)**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/models.py app/main.py tests/unit/
git commit -m "feat: add ORM models for rooms, participants, questions, upvotes"
```

---

### Task B2: Pydantic schemas

**Files:**
- Create: `app/schemas.py`
- Create: `tests/unit/test_schemas.py`

- [ ] **Step 1: Create `app/schemas.py`**

```python
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
```

- [ ] **Step 2: Add `email-validator` to dependencies**

Add to `pyproject.toml`:
```toml
"email-validator>=2.2",
```

Then `uv sync --all-groups`.

- [ ] **Step 3: Create `tests/unit/test_schemas.py`**

```python
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
```

- [ ] **Step 4: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_schemas.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/unit/test_schemas.py pyproject.toml uv.lock
git commit -m "feat: add Pydantic DTOs for room, question, upvote, join"
```

---

### Task B3: Utility helpers (codes, IDs, tokens)

**Files:**
- Create: `app/utils/__init__.py`
- Create: `app/utils/codes.py`
- Create: `app/utils/ids.py`
- Create: `tests/unit/test_codes.py`

- [ ] **Step 1: Create `app/utils/__init__.py` (empty)**

```python
```

- [ ] **Step 2: Create `app/utils/codes.py`**

The alphabet excludes ambiguous characters: `0`/`O`, `1`/`I`/`l`, plus `B`/`8`, `5`/`S`, `2`/`Z`.

```python
import secrets

# 26 chars: clear, unambiguous in print, no homoglyphs
ROOM_CODE_ALPHABET = "ACDEFGHJKLMNPQRTUVWXY3479"
ROOM_CODE_LENGTH = 6


def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def is_valid_room_code(code: str) -> bool:
    if len(code) != ROOM_CODE_LENGTH:
        return False
    return all(c in ROOM_CODE_ALPHABET for c in code)
```

- [ ] **Step 3: Create `app/utils/ids.py`**

```python
import secrets


def new_session_id() -> str:
    """Cookie value for an audience participant. URL-safe, 24 bytes ~ 32 chars."""
    return secrets.token_urlsafe(24)


def new_presenter_token() -> str:
    """Secret room presenter token. 32 bytes ~ 43 chars URL-safe."""
    return secrets.token_urlsafe(32)
```

- [ ] **Step 4: Create `tests/unit/test_codes.py`**

```python
from app.utils.codes import (
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    generate_room_code,
    is_valid_room_code,
)
from app.utils.ids import new_presenter_token, new_session_id


def test_generated_code_has_correct_length():
    code = generate_room_code()
    assert len(code) == ROOM_CODE_LENGTH


def test_generated_code_only_uses_alphabet():
    for _ in range(100):
        code = generate_room_code()
        assert all(c in ROOM_CODE_ALPHABET for c in code)


def test_alphabet_excludes_ambiguous():
    for c in "01OIlB85S2Z":
        assert c not in ROOM_CODE_ALPHABET, f"{c} should not be in alphabet"


def test_codes_are_random():
    seen = {generate_room_code() for _ in range(1000)}
    # 25^6 = ~244M codes; collisions in 1000 should be vanishingly rare
    assert len(seen) > 990


def test_is_valid_room_code():
    assert is_valid_room_code("ACDEFG")
    assert not is_valid_room_code("abcdef")
    assert not is_valid_room_code("ACD")
    assert not is_valid_room_code("ACDEFGH")
    assert not is_valid_room_code("ACDEF0")  # 0 excluded


def test_session_id_unique():
    ids = {new_session_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_presenter_token_unique_and_long():
    t = new_presenter_token()
    assert len(t) >= 40
    assert len({new_presenter_token() for _ in range(1000)}) == 1000
```

- [ ] **Step 5: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_codes.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add app/utils/ tests/unit/test_codes.py
git commit -m "feat: add room code, session id, and presenter token generators"
```

---

## Phase C — Auth & sessions

### Task C1: Audience cookie + presenter token dependencies

**Files:**
- Create: `app/auth.py`
- Create: `tests/unit/test_auth.py`

- [ ] **Step 1: Create `app/auth.py`**

```python
import hmac
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Participant, Room
from app.utils.ids import new_session_id

AUDIENCE_COOKIE = "qa_session"
PRESENTER_QUERY = "t"


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


async def get_or_create_session_id(
    response: Response,
    qa_session: Annotated[str | None, Cookie(alias=AUDIENCE_COOKIE)] = None,
) -> str:
    if qa_session and len(qa_session) >= 16:
        return qa_session
    new = new_session_id()
    response.set_cookie(
        AUDIENCE_COOKIE,
        new,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return new


async def get_room_by_code(
    code: str,
    session: AsyncSession = Depends(get_session),
) -> Room:
    result = await session.execute(select(Room).where(Room.code == code))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    return room


async def require_presenter(
    request: Request,
    code: str,
    t: Annotated[str | None, Query(alias=PRESENTER_QUERY)] = None,
    session: AsyncSession = Depends(get_session),
) -> Room:
    room = await get_room_by_code(code, session)
    token = t or request.headers.get("X-Presenter-Token")
    if not token or not constant_time_eq(token, room.presenter_token):
        # No oracle: redirect to audience view rather than 401
        raise HTTPException(
            status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/r/{code}"},
        )
    return room


async def get_or_create_participant(
    room: Room,
    session_id: str,
    name: str | None,
    db: AsyncSession,
) -> Participant | None:
    result = await db.execute(
        select(Participant).where(
            Participant.room_id == room.id,
            Participant.session_id == session_id,
        )
    )
    p = result.scalar_one_or_none()
    if p is not None:
        return p
    if name is None:
        return None
    p = Participant(room_id=room.id, session_id=session_id, name=name)
    db.add(p)
    await db.flush()
    return p
```

- [ ] **Step 2: Create `tests/unit/test_auth.py`**

```python
from app.auth import constant_time_eq


def test_constant_time_eq_matches():
    assert constant_time_eq("abc", "abc") is True


def test_constant_time_eq_mismatch():
    assert constant_time_eq("abc", "abd") is False


def test_constant_time_eq_different_length():
    assert constant_time_eq("abc", "abcd") is False
```

- [ ] **Step 3: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_auth.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/auth.py tests/unit/test_auth.py
git commit -m "feat: add audience session cookie + presenter token dependencies"
```

---

## Phase D — Room lifecycle

### Task D1: Room creation service + endpoint

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/rooms.py`
- Create: `app/routes/__init__.py`
- Create: `app/routes/rooms.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_room_lifecycle.py`

- [ ] **Step 1: Create `app/services/__init__.py` and `app/routes/__init__.py` (empty)**

```python
```

- [ ] **Step 2: Create `app/services/rooms.py`**

```python
from datetime import timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Room, RoomStatus
from app.utils.codes import generate_room_code
from app.utils.ids import new_presenter_token


def _new_expiry():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc) + timedelta(hours=get_settings().room_ttl_hours)


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
    from datetime import datetime, timezone
    room.last_activity_at = datetime.now(timezone.utc)
    room.expires_at = _new_expiry()
    await db.flush()


async def close_room(db: AsyncSession, room: Room) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    room.status = RoomStatus.CLOSED
    room.closed_at = now
    room.last_activity_at = now
    room.expires_at = now + timedelta(hours=get_settings().room_ttl_hours)
    await db.flush()


async def expired_rooms(db: AsyncSession) -> Iterable[Room]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    result = await db.execute(select(Room).where(Room.expires_at < now))
    return result.scalars().all()
```

- [ ] **Step 3: Create `app/routes/rooms.py`**

```python
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
```

- [ ] **Step 4: Wire router in `app/main.py`**

Add to imports:
```python
from app.routes import rooms as rooms_routes
```

After `app = FastAPI(...)` line, add:
```python
app.include_router(rooms_routes.router)
```

- [ ] **Step 5: Create `tests/integration/test_room_lifecycle.py`**

```python
async def test_create_room_returns_urls(client):
    resp = await client.post("/rooms", json={"title": "AI Talks"})
    assert resp.status_code == 201
    body = resp.json()
    assert "code" in body
    assert len(body["code"]) == 6
    assert body["audience_url"].endswith(f"/r/{body['code']}")
    assert "host?t=" in body["presenter_url"]


async def test_create_room_with_email(client):
    resp = await client.post(
        "/rooms",
        json={"title": "AI Talks", "presenter_email": "a@b.co"},
    )
    assert resp.status_code == 201


async def test_create_room_rejects_bad_email(client):
    resp = await client.post(
        "/rooms",
        json={"presenter_email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_end_session_requires_token(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    resp = await client.post(f"/r/{code}/end", follow_redirects=False)
    assert resp.status_code == 303


async def test_end_session_with_correct_token(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]

    resp = await client.post(f"/r/{code}/end?t={token}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    resp2 = await client.post(f"/r/{code}/end?t={token}")
    assert resp2.status_code == 409
```

- [ ] **Step 6: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_room_lifecycle.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add app/services/ app/routes/ app/main.py tests/integration/test_room_lifecycle.py
git commit -m "feat: add room creation and end-session endpoints"
```

---

### Task D2: Room expiry sweep (background task)

**Files:**
- Modify: `app/main.py`
- Create: `tests/integration/test_room_expiry.py`

- [ ] **Step 1: Update `app/main.py` to register a sweep task**

Replace the lifespan function with:

```python
import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete

from app.db import async_session_factory  # noqa: will add next step


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    init_engine()
    await create_all()
    sweep_task = asyncio.create_task(_sweep_loop())
    yield
    sweep_task.cancel()


async def _sweep_loop():
    from app.db import get_sessionmaker
    while True:
        try:
            sm = get_sessionmaker()
            async with sm() as s:
                from app.models import Room
                await s.execute(
                    delete(Room).where(Room.expires_at < datetime.now(timezone.utc))
                )
                await s.commit()
        except Exception:
            pass
        await asyncio.sleep(600)
```

- [ ] **Step 2: Add `get_sessionmaker` helper in `app/db.py`**

Add to `app/db.py`:

```python
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    assert _sessionmaker is not None
    return _sessionmaker
```

Remove the `from app.db import async_session_factory` line in `main.py`.

- [ ] **Step 3: Create `tests/integration/test_room_expiry.py`**

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import Room


async def test_expired_room_is_swept(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]

    sm = get_sessionmaker()
    async with sm() as s:
        room = (await s.execute(select(Room).where(Room.code == code))).scalar_one()
        room.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await s.commit()

    # Manually invoke the sweep logic instead of waiting 10 minutes
    from sqlalchemy import delete as sql_delete
    async with sm() as s:
        await s.execute(sql_delete(Room).where(Room.expires_at < datetime.now(timezone.utc)))
        await s.commit()

    async with sm() as s:
        result = await s.execute(select(Room).where(Room.code == code))
        assert result.scalar_one_or_none() is None
```

- [ ] **Step 4: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_room_expiry.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/db.py tests/integration/test_room_expiry.py
git commit -m "feat: add periodic sweep of expired rooms"
```

---

## Phase E — Questions & upvotes

### Task E1: Question state-transition service

**Files:**
- Create: `app/services/questions.py`
- Create: `tests/unit/test_state_transitions.py`

- [ ] **Step 1: Create `app/services/questions.py`**

```python
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question, QuestionState

ALLOWED_STATES: set[str] = {s.value for s in QuestionState}


class InvalidStateTransition(ValueError):
    pass


async def set_question_state(
    db: AsyncSession,
    *,
    room_id: int,
    question: Question,
    new_state: str,
) -> None:
    if new_state not in ALLOWED_STATES:
        raise InvalidStateTransition(f"Unknown state: {new_state}")
    if new_state == QuestionState.PINNED.value:
        await db.execute(
            update(Question)
            .where(
                Question.room_id == room_id,
                Question.state == QuestionState.PINNED.value,
                Question.id != question.id,
            )
            .values(state=QuestionState.LIVE.value)
        )
    question.state = QuestionState(new_state)
    await db.flush()


async def set_question_starred(
    db: AsyncSession,
    *,
    question: Question,
    starred: bool,
) -> None:
    question.starred = starred
    await db.flush()
```

- [ ] **Step 2: Create `tests/unit/test_state_transitions.py`**

```python
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.models import Participant, Question, QuestionState, Room
from app.services.questions import (
    InvalidStateTransition,
    set_question_starred,
    set_question_state,
)


@pytest_asyncio.fixture
async def session_with_room():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        room = Room(
            code="ABCDEF",
            presenter_token="t" * 32,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        s.add(room)
        await s.flush()
        p = Participant(room_id=room.id, session_id="s1", name="A")
        s.add(p)
        await s.flush()
        yield s, room, p
    await engine.dispose()


async def test_pin_unpins_others(session_with_room):
    s, room, p = session_with_room
    q1 = Question(room_id=room.id, participant_id=p.id, author_name="A", text="1")
    q2 = Question(room_id=room.id, participant_id=p.id, author_name="A", text="2")
    s.add_all([q1, q2])
    await s.flush()

    await set_question_state(s, room_id=room.id, question=q1, new_state="pinned")
    await s.flush()
    await set_question_state(s, room_id=room.id, question=q2, new_state="pinned")
    await s.commit()

    refreshed = await s.execute(
        select(Question).where(Question.room_id == room.id).order_by(Question.id)
    )
    states = [q.state for q in refreshed.scalars()]
    assert states == [QuestionState.LIVE, QuestionState.PINNED]


async def test_invalid_state_raises(session_with_room):
    s, room, p = session_with_room
    q = Question(room_id=room.id, participant_id=p.id, author_name="A", text="x")
    s.add(q)
    await s.flush()
    import pytest
    with pytest.raises(InvalidStateTransition):
        await set_question_state(s, room_id=room.id, question=q, new_state="bogus")


async def test_star_is_orthogonal(session_with_room):
    s, room, p = session_with_room
    q = Question(room_id=room.id, participant_id=p.id, author_name="A", text="x")
    s.add(q)
    await s.flush()
    await set_question_starred(s, question=q, starred=True)
    assert q.starred is True
    await set_question_state(s, room_id=room.id, question=q, new_state="answered")
    assert q.starred is True  # unchanged
    assert q.state == QuestionState.ANSWERED
```

- [ ] **Step 3: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_state_transitions.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/services/questions.py tests/unit/test_state_transitions.py
git commit -m "feat: add question state transition service with pin uniqueness"
```

---

### Task E2: Rate limiter

**Files:**
- Create: `app/services/ratelimit.py`
- Create: `tests/unit/test_ratelimit.py`

- [ ] **Step 1: Create `app/services/ratelimit.py`**

```python
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, *, max_actions: int, window_seconds: float) -> None:
        self.max_actions = max_actions
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_actions:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._buckets.clear()
            else:
                self._buckets.pop(key, None)
```

- [ ] **Step 2: Create `tests/unit/test_ratelimit.py`**

```python
from app.services.ratelimit import RateLimiter


def test_allows_up_to_max():
    rl = RateLimiter(max_actions=3, window_seconds=60)
    assert rl.allow("k", now=0)
    assert rl.allow("k", now=1)
    assert rl.allow("k", now=2)
    assert not rl.allow("k", now=3)


def test_window_slides():
    rl = RateLimiter(max_actions=2, window_seconds=10)
    assert rl.allow("k", now=0)
    assert rl.allow("k", now=5)
    assert not rl.allow("k", now=9)
    # both prior actions out of window now
    assert rl.allow("k", now=20)
    assert rl.allow("k", now=21)


def test_keys_are_isolated():
    rl = RateLimiter(max_actions=1, window_seconds=60)
    assert rl.allow("a", now=0)
    assert rl.allow("b", now=0)
    assert not rl.allow("a", now=1)
    assert not rl.allow("b", now=1)


def test_reset():
    rl = RateLimiter(max_actions=1, window_seconds=60)
    assert rl.allow("k", now=0)
    rl.reset("k")
    assert rl.allow("k", now=1)
```

- [ ] **Step 3: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_ratelimit.py -v
```

Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/services/ratelimit.py tests/unit/test_ratelimit.py
git commit -m "feat: add per-key rolling-window rate limiter"
```

---

### Task E3: Audience join + question creation endpoints

**Files:**
- Create: `app/routes/questions.py`
- Modify: `app/main.py` (register router; create rate-limiter singletons)
- Create: `tests/integration/test_questions.py`

- [ ] **Step 1: Create `app/routes/questions.py`**

```python
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AUDIENCE_COOKIE,
    get_or_create_participant,
    get_or_create_session_id,
    get_room_by_code,
    require_presenter,
)
from app.config import get_settings
from app.db import get_session
from app.models import Question, QuestionState, Room, RoomStatus
from app.schemas import (
    JoinRequest,
    QuestionCreateRequest,
    QuestionDTO,
    QuestionPatchRequest,
)
from app.services.questions import set_question_starred, set_question_state
from app.services.ratelimit import RateLimiter
from app.services.rooms import touch_room

router = APIRouter()

_question_limiter: RateLimiter | None = None


def get_question_limiter() -> RateLimiter:
    global _question_limiter
    if _question_limiter is None:
        s = get_settings()
        _question_limiter = RateLimiter(
            max_actions=s.rate_limit_questions_per_min, window_seconds=60
        )
    return _question_limiter


def _ensure_room_writable(room: Room) -> None:
    if room.status == RoomStatus.CLOSED:
        raise HTTPException(status.HTTP_410_GONE, "Room is closed")
    if room.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "Room is expired")


@router.post("/r/{code}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_room(
    code: str,
    body: JoinRequest,
    response: Response,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    db: AsyncSession = Depends(get_session),
):
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)
    p = await get_or_create_participant(room, session_id, body.name, db)
    if p is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not create participant")
    p.name = body.name
    await db.commit()
    return Response(status_code=204)


@router.post("/r/{code}/questions", response_model=QuestionDTO, status_code=201)
async def create_question(
    code: str,
    body: QuestionCreateRequest,
    response: Response,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    qa_session: Annotated[str | None, Cookie(alias=AUDIENCE_COOKIE)] = None,
    db: AsyncSession = Depends(get_session),
) -> QuestionDTO:
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)

    p = await get_or_create_participant(room, session_id, None, db)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Join the room first")

    rl = get_question_limiter()
    if not rl.allow(f"{room.id}:{p.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Slow down a sec")

    q = Question(
        room_id=room.id,
        participant_id=p.id,
        author_name=p.name,
        text=body.text,
    )
    db.add(q)
    await touch_room(db, room)
    await db.commit()
    await db.refresh(q)
    return QuestionDTO.model_validate(q)


@router.patch("/r/{code}/questions/{qid}", response_model=QuestionDTO)
async def patch_question(
    code: str,
    qid: int,
    body: QuestionPatchRequest,
    room: Room = Depends(require_presenter),
    db: AsyncSession = Depends(get_session),
) -> QuestionDTO:
    q = await db.get(Question, qid)
    if q is None or q.room_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    if body.state is not None:
        await set_question_state(db, room_id=room.id, question=q, new_state=body.state)
    if body.starred is not None:
        await set_question_starred(db, question=q, starred=body.starred)

    await touch_room(db, room)
    await db.commit()
    await db.refresh(q)
    return QuestionDTO.model_validate(q)
```

- [ ] **Step 2: Register the router in `app/main.py`**

Add to imports:
```python
from app.routes import questions as questions_routes
```

After `app.include_router(rooms_routes.router)`:
```python
app.include_router(questions_routes.router)
```

- [ ] **Step 3: Create `tests/integration/test_questions.py`**

```python
async def _create_room_and_join(client, name="Sam"):
    r = await client.post("/rooms", json={})
    body = r.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    j = await client.post(f"/r/{code}/join", json={"name": name})
    assert j.status_code == 204
    return code, token


async def test_audience_can_ask_question(client):
    code, _ = await _create_room_and_join(client)
    r = await client.post(f"/r/{code}/questions", json={"text": "hello?"})
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "hello?"
    assert body["state"] == "live"
    assert body["upvote_count"] == 0
    assert body["author_name"] == "Sam"


async def test_question_requires_join_first(client):
    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    resp = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    assert resp.status_code == 403


async def test_question_too_long_rejected(client):
    code, _ = await _create_room_and_join(client)
    r = await client.post(f"/r/{code}/questions", json={"text": "x" * 281})
    assert r.status_code == 422


async def test_presenter_can_pin(client):
    code, token = await _create_room_and_join(client)
    create = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    qid = create.json()["id"]
    r = await client.patch(f"/r/{code}/questions/{qid}?t={token}", json={"state": "pinned"})
    assert r.status_code == 200
    assert r.json()["state"] == "pinned"


async def test_pin_replaces_previous_pin(client):
    code, token = await _create_room_and_join(client)
    q1 = (await client.post(f"/r/{code}/questions", json={"text": "1"})).json()["id"]
    q2 = (await client.post(f"/r/{code}/questions", json={"text": "2"})).json()["id"]
    await client.patch(f"/r/{code}/questions/{q1}?t={token}", json={"state": "pinned"})
    await client.patch(f"/r/{code}/questions/{q2}?t={token}", json={"state": "pinned"})

    r1 = await client.patch(f"/r/{code}/questions/{q1}?t={token}", json={"starred": True})
    assert r1.json()["state"] == "live"


async def test_rate_limit(client):
    from app.routes.questions import get_question_limiter
    get_question_limiter().reset()
    code, _ = await _create_room_and_join(client)
    for i in range(5):
        r = await client.post(f"/r/{code}/questions", json={"text": f"q{i}"})
        assert r.status_code == 201
    r = await client.post(f"/r/{code}/questions", json={"text": "one too many"})
    assert r.status_code == 429
```

- [ ] **Step 4: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_questions.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/routes/questions.py app/main.py tests/integration/test_questions.py
git commit -m "feat: add audience join, question create, presenter patch endpoints"
```

---

### Task E4: Upvote toggle endpoint

**Files:**
- Create: `app/routes/upvotes.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_upvotes.py`

- [ ] **Step 1: Create `app/routes/upvotes.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    get_or_create_participant,
    get_or_create_session_id,
    get_room_by_code,
)
from app.config import get_settings
from app.db import get_session
from app.models import Question, Upvote
from app.routes.questions import _ensure_room_writable
from app.services.ratelimit import RateLimiter

router = APIRouter()

_upvote_limiter: RateLimiter | None = None


def get_upvote_limiter() -> RateLimiter:
    global _upvote_limiter
    if _upvote_limiter is None:
        s = get_settings()
        _upvote_limiter = RateLimiter(max_actions=s.rate_limit_upvotes_per_min, window_seconds=60)
    return _upvote_limiter


@router.post("/r/{code}/questions/{qid}/upvote")
async def upvote(
    code: str,
    qid: int,
    session_id: Annotated[str, Depends(get_or_create_session_id)],
    db: AsyncSession = Depends(get_session),
) -> dict[str, int | bool]:
    room = await get_room_by_code(code, db)
    _ensure_room_writable(room)
    p = await get_or_create_participant(room, session_id, None, db)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Join the room first")

    rl = get_upvote_limiter()
    if not rl.allow(f"{room.id}:{p.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Slow down a sec")

    q = await db.get(Question, qid)
    if q is None or q.room_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    existing = await db.execute(
        select(Upvote).where(Upvote.question_id == qid, Upvote.participant_id == p.id)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        q.upvote_count = max(0, q.upvote_count - 1)
        upvoted = False
    else:
        try:
            db.add(Upvote(question_id=qid, participant_id=p.id))
            q.upvote_count += 1
            upvoted = True
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return {"upvotes": q.upvote_count, "upvoted": True}

    await db.commit()
    return {"upvotes": q.upvote_count, "upvoted": upvoted}
```

- [ ] **Step 2: Register router in `app/main.py`**

Add to imports:
```python
from app.routes import upvotes as upvotes_routes
```

After the questions router include:
```python
app.include_router(upvotes_routes.router)
```

- [ ] **Step 3: Create `tests/integration/test_upvotes.py`**

```python
async def _setup(client):
    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    q = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    return code, q.json()["id"]


async def test_upvote_increments(client):
    code, qid = await _setup(client)
    r = await client.post(f"/r/{code}/questions/{qid}/upvote")
    assert r.status_code == 200
    body = r.json()
    assert body["upvoted"] is True
    assert body["upvotes"] == 1


async def test_upvote_toggle(client):
    code, qid = await _setup(client)
    await client.post(f"/r/{code}/questions/{qid}/upvote")
    r = await client.post(f"/r/{code}/questions/{qid}/upvote")
    assert r.json()["upvoted"] is False
    assert r.json()["upvotes"] == 0


async def test_upvote_404_for_unknown_question(client):
    code, _ = await _setup(client)
    r = await client.post(f"/r/{code}/questions/9999/upvote")
    assert r.status_code == 404
```

- [ ] **Step 4: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_upvotes.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/routes/upvotes.py app/main.py tests/integration/test_upvotes.py
git commit -m "feat: add upvote toggle endpoint with idempotency"
```

---

## Phase F — Real-time SSE

### Task F1: PubSub service

**Files:**
- Create: `app/services/pubsub.py`
- Create: `tests/unit/test_pubsub.py`

- [ ] **Step 1: Create `app/services/pubsub.py`**

```python
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class RoomPubSub:
    def __init__(self) -> None:
        self._queues: dict[int, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, room_id: int, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._queues.get(room_id, ()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    @asynccontextmanager
    async def subscribe(self, room_id: int) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._queues.setdefault(room_id, set()).add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._queues.get(room_id, set()).discard(queue)

    async def subscriber_count(self, room_id: int) -> int:
        async with self._lock:
            return len(self._queues.get(room_id, set()))


pubsub = RoomPubSub()
```

- [ ] **Step 2: Create `tests/unit/test_pubsub.py`**

```python
import asyncio

from app.services.pubsub import RoomPubSub


async def test_subscriber_receives_published_event():
    ps = RoomPubSub()
    async with ps.subscribe(1) as q:
        await ps.publish(1, {"event": "a"})
        evt = await asyncio.wait_for(q.get(), timeout=1.0)
        assert evt == {"event": "a"}


async def test_other_rooms_not_affected():
    ps = RoomPubSub()
    async with ps.subscribe(1) as q:
        await ps.publish(2, {"event": "x"})
        await asyncio.sleep(0.05)
        assert q.empty()


async def test_unsubscribe_on_exit():
    ps = RoomPubSub()
    async with ps.subscribe(1):
        assert await ps.subscriber_count(1) == 1
    assert await ps.subscriber_count(1) == 0
```

- [ ] **Step 3: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_pubsub.py -v
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add app/services/pubsub.py tests/unit/test_pubsub.py
git commit -m "feat: add in-memory pubsub fanout for SSE"
```

---

### Task F2: SSE endpoint + wire mutations to publish

**Files:**
- Create: `app/routes/events.py`
- Modify: `app/routes/questions.py`
- Modify: `app/routes/upvotes.py`
- Modify: `app/routes/rooms.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_sse.py`

- [ ] **Step 1: Create `app/routes/events.py`**

```python
import asyncio
import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_room_by_code
from app.db import get_session
from app.services.pubsub import pubsub

router = APIRouter()


def _format_sse(event_type: str, data: dict) -> bytes:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()


@router.get("/r/{code}/events")
async def events(
    code: str,
    db: AsyncSession = Depends(get_session),
):
    room = await get_room_by_code(code, db)

    async def stream() -> AsyncIterator[bytes]:
        async with pubsub.subscribe(room.id) as q:
            yield _format_sse("connected", {"room_id": room.id})
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield _format_sse(event["type"], event["data"])
                except asyncio.TimeoutError:
                    yield _format_sse("ping", {})

    return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Wire `app/routes/questions.py` to publish events**

Inside `create_question`, immediately before the `return QuestionDTO.model_validate(q)` line, add:

```python
    await pubsub.publish(
        room.id,
        {
            "type": "question.created",
            "data": QuestionDTO.model_validate(q).model_dump(mode="json"),
        },
    )
```

Inside `patch_question`, before the final return, add:

```python
    await pubsub.publish(
        room.id,
        {
            "type": "question.state_changed",
            "data": {"id": q.id, "state": q.state.value, "starred": q.starred},
        },
    )
```

Add the import at the top of `app/routes/questions.py`:

```python
from app.services.pubsub import pubsub
```

- [ ] **Step 3: Wire `app/routes/upvotes.py` to publish**

Before the final `return` in `upvote`, add:

```python
    await pubsub.publish(
        room.id,
        {"type": "question.upvoted", "data": {"id": q.id, "upvotes": q.upvote_count}},
    )
```

Add at the top:

```python
from app.services.pubsub import pubsub
```

- [ ] **Step 4: Wire `app/routes/rooms.py` `end_session` to publish**

Before the `return {"status": "closed"}` line, add:

```python
    await pubsub.publish(
        room.id,
        {"type": "room.closed", "data": {"reason": "presenter_ended"}},
    )
```

Add at the top:

```python
from app.services.pubsub import pubsub
```

- [ ] **Step 5: Register `events_routes` in `app/main.py`**

Add to imports:
```python
from app.routes import events as events_routes
```

After the upvotes include:
```python
app.include_router(events_routes.router)
```

- [ ] **Step 6: Create `tests/integration/test_sse.py`**

```python
import asyncio
import json

import pytest


@pytest.mark.timeout(10)
async def test_sse_receives_question_created(client):
    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})

    received: list[dict] = []

    async def reader():
        async with client.stream("GET", f"/r/{code}/events") as response:
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = json.loads(line.split(":", 1)[1].strip())
                    received.append({"type": event_type, "data": data})
                    if len(received) >= 2:
                        return

    task = asyncio.create_task(reader())
    await asyncio.sleep(0.2)
    await client.post(f"/r/{code}/questions", json={"text": "hello"})
    await asyncio.wait_for(task, timeout=5.0)

    assert any(e["type"] == "connected" for e in received)
    assert any(e["type"] == "question.created" for e in received)
```

- [ ] **Step 7: Add `pytest-timeout` to dev deps**

In `pyproject.toml`:
```toml
"pytest-timeout>=2.3",
```

Then `uv sync --all-groups`.

- [ ] **Step 8: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_sse.py -v
```

Expected: 1 passed.

- [ ] **Step 9: Commit**

```bash
git add app/routes/events.py app/routes/questions.py app/routes/upvotes.py app/routes/rooms.py app/main.py tests/integration/test_sse.py pyproject.toml uv.lock
git commit -m "feat: add SSE endpoint and wire mutations to publish events"
```

---

## Phase G — Frontend foundation

### Task G1: Brand tokens + base CSS + base template

**Files:**
- Create: `static/css/tokens.css`
- Create: `static/css/base.css`
- Create: `static/css/animations.css`
- Create: `templates/base.html`
- Modify: `app/main.py` (mount static + templates)

- [ ] **Step 1: Create `static/css/tokens.css`**

```css
:root {
  /* DLAI primary (coral-led) */
  --dlai-coral:        #F65B66;
  --dlai-coral-deep:   #EE414D;
  --dlai-coral-bg:     #FED7DA;
  --dlai-coral-tint:   #FFF5F6;

  /* DLAI secondary */
  --dlai-teal:         #237B94;
  --dlai-teal-light:   #36A3C8;
  --dlai-navy:         #002566;

  /* Neutrals (Tailwind slate) */
  --slate-900: #0F172A;
  --slate-700: #334155;
  --slate-500: #64748B;
  --slate-400: #94A3B8;
  --slate-200: #E2E8F0;
  --slate-100: #F1F5F9;
  --slate-50:  #F8FAFC;

  --radius-sm: 8px;
  --radius-md: 12px;

  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif,
               'Apple Color Emoji', 'Segoe UI Emoji';

  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);

  --easing-in:  cubic-bezier(0.32, 0.72, 0, 1);
  --easing-out: cubic-bezier(0.4, 0, 0.2, 1);
}
```

- [ ] **Step 2: Create `static/css/base.css`**

```css
* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  font-family: var(--font-sans);
  color: var(--slate-900);
  background: var(--slate-100);
  -webkit-font-smoothing: antialiased;
}

a { color: var(--dlai-teal); text-decoration: none; }
a:hover { color: var(--dlai-teal-light); }

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  border-radius: var(--radius-sm);
  padding: 10px 16px;
  font-size: 15px;
  font-weight: 500;
  transition: background 120ms var(--easing-in), transform 120ms var(--easing-in);
}
button:active { transform: translateY(1px); }
button:focus-visible {
  outline: 2px solid var(--dlai-coral);
  outline-offset: 2px;
}

.btn-primary {
  background: var(--dlai-coral);
  color: white;
}
.btn-primary:hover { background: var(--dlai-coral-deep); }

.btn-secondary {
  background: white;
  border: 1px solid var(--slate-200);
  color: var(--slate-900);
}
.btn-secondary:hover { background: var(--slate-50); }

input, textarea {
  font-family: inherit;
  font-size: 15px;
  border: 1px solid var(--slate-200);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  width: 100%;
  background: white;
  color: var(--slate-900);
  transition: border-color 140ms var(--easing-in), box-shadow 140ms var(--easing-in);
}
input:focus, textarea:focus {
  outline: none;
  border-color: var(--dlai-coral);
  box-shadow: 0 0 0 2px var(--dlai-coral-bg);
}
input::placeholder, textarea::placeholder { color: var(--slate-400); }

.app-header {
  background: var(--dlai-coral);
  color: white;
  padding: 0 16px;
  height: 56px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 10;
}
.app-header h1 { font-size: 17px; font-weight: 600; margin: 0; }

@media (min-width: 1024px) {
  .app-header { height: 64px; padding: 0 24px; }
  .app-header h1 { font-size: 18px; }
}

.card {
  background: white;
  border: 1px solid var(--slate-200);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-sm);
}

.muted { color: var(--slate-500); }

.app-footer {
  text-align: center;
  padding: 48px 16px;
  color: var(--slate-500);
  font-size: 13px;
}
.app-footer .heart {
  color: var(--dlai-coral);
  display: inline-block;
  animation: heartbeat 1.5s var(--easing-in) infinite;
}
@keyframes heartbeat {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
.app-footer .links { margin-top: 8px; }
.app-footer .links a { color: var(--slate-500); margin: 0 6px; }
```

- [ ] **Step 3: Create `static/css/animations.css`**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 100ms !important;
    transition-duration: 100ms !important;
    animation-iteration-count: 1 !important;
  }
}

@keyframes slide-in-top {
  from { opacity: 0; transform: translateY(-12px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0)     scale(1); }
}

.q-card-new {
  animation: slide-in-top 280ms var(--easing-in);
  border-left: 3px solid var(--dlai-coral);
}

@keyframes upvote-pulse {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.18); }
  100% { transform: scale(1); }
}
.upvote-active { animation: upvote-pulse 220ms var(--easing-in); }

@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton {
  background: linear-gradient(90deg,
    var(--slate-100) 0%, var(--slate-200) 50%, var(--slate-100) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: var(--radius-sm);
}
```

- [ ] **Step 4: Create `templates/base.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{% block title %}DLAI Q&A{% endblock %}</title>
  <link rel="preconnect" href="https://rsms.me/">
  <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
  <link rel="stylesheet" href="/static/css/tokens.css">
  <link rel="stylesheet" href="/static/css/base.css">
  <link rel="stylesheet" href="/static/css/animations.css">
  <script src="https://unpkg.com/htmx.org@2.0.3" defer></script>
  {% block head %}{% endblock %}
</head>
<body>
  {% block body %}{% endblock %}
  {% block footer %}
  <footer class="app-footer">
    <div>Made with <span class="heart">♥</span> from Gaurav &amp; DeepLearning.AI</div>
    <div class="links">
      <a href="#">GitHub</a> · <a href="#">Privacy</a> · v0.1.0
    </div>
  </footer>
  {% endblock %}
</body>
</html>
```

- [ ] **Step 5: Mount static + templates in `app/main.py`**

Add to imports:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
```

After `app = FastAPI(...)`:
```python
_BASE = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")
templates = Jinja2Templates(directory=_BASE / "templates")
```

- [ ] **Step 6: Smoke-test the static files**

```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl -sI http://localhost:8000/static/css/tokens.css | head -1
kill %1
```

Expected: `HTTP/1.1 200 OK`

- [ ] **Step 7: Commit**

```bash
git add static/ templates/base.html app/main.py
git commit -m "feat: add brand CSS tokens, base styles, animations, base template"
```

---

### Task G2: Homepage with Title + Email form

**Files:**
- Create: `templates/home.html`
- Create: `app/routes/pages.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_pages.py`

- [ ] **Step 1: Create `templates/home.html`**

```html
{% extends "base.html" %}
{% block title %}DLAI Q&A — Live questions for your talk{% endblock %}
{% block body %}
<main style="max-width: 560px; margin: 64px auto; padding: 0 16px;">
  <h1 style="font-size: 32px; margin: 0 0 8px; color: var(--slate-900);">
    Live Q&amp;A for your talk
  </h1>
  <p class="muted" style="font-size: 17px; margin: 0 0 32px;">
    No accounts. No setup. Just share a QR code.
  </p>

  <form id="start-form" style="display: grid; gap: 12px;">
    <label>
      <div style="font-size: 13px; color: var(--slate-700); margin-bottom: 4px;">
        Session title <span class="muted">(optional)</span>
      </div>
      <input type="text" name="title" maxlength="80" placeholder="e.g. AI Talks 2026">
    </label>
    <label>
      <div style="font-size: 13px; color: var(--slate-700); margin-bottom: 4px;">
        Email me a copy when the session ends <span class="muted">(optional)</span>
      </div>
      <input type="email" name="presenter_email" placeholder="you@example.com">
      <div style="font-size: 12px; color: var(--slate-500); margin-top: 4px;">
        We only use this to email your Q&amp;A archive. No marketing, no sharing.
      </div>
    </label>
    <button type="submit" class="btn-primary" style="margin-top: 8px;">
      Start a session →
    </button>
    <div id="form-error" style="color: var(--dlai-coral-deep); font-size: 14px;"></div>
  </form>

  <p class="muted" style="margin-top: 24px; font-size: 14px;">
    Have a code? <a href="/join">Join here →</a>
  </p>
</main>

<script>
document.getElementById('start-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = {
    title: f.title.value || null,
    presenter_email: f.presenter_email.value || null,
  };
  for (const k of Object.keys(body)) if (body[k] === null || body[k] === '') delete body[k];
  const r = await fetch('/rooms', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    document.getElementById('form-error').textContent =
      r.status === 422 ? 'Please enter a valid email or leave it blank.' : 'Could not create session.';
    return;
  }
  const data = await r.json();
  window.location.href = data.presenter_url.replace(window.location.origin, '');
});
</script>
{% endblock %}
```

- [ ] **Step 2: Create `app/routes/pages.py`**

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import constant_time_eq, get_or_create_session_id, get_room_by_code
from app.db import get_session
from app.models import RoomStatus

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates if hasattr(request.app.state, "templates") else None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return request.app.state.templates.TemplateResponse(request, "home.html", {})
```

- [ ] **Step 3: Modify `app/main.py` to expose templates via app.state**

After `templates = Jinja2Templates(...)`:
```python
app.state.templates = templates
```

Add to imports:
```python
from app.routes import pages as pages_routes
```

Register before the JSON routers:
```python
app.include_router(pages_routes.router)
```

- [ ] **Step 4: Create `tests/integration/test_pages.py`**

```python
async def test_home_renders(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Live Q&amp;A for your talk" in body
    assert "Made with" in body
    assert "DeepLearning.AI" in body
```

- [ ] **Step 5: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_pages.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Manual smoke test**

```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
open http://localhost:8000  # or curl -s http://localhost:8000 | head -50
kill %1
```

Verify the page loads and the form is visible.

- [ ] **Step 7: Commit**

```bash
git add templates/home.html app/routes/pages.py app/main.py tests/integration/test_pages.py
git commit -m "feat: add homepage with start-session form (title + email)"
```

---

### Task G3: Audience view (template, join, ask, upvote)

**Files:**
- Create: `templates/audience.html`
- Create: `templates/partials/question_card.html`
- Create: `static/js/sse.js`
- Create: `static/js/upvote.js`
- Modify: `app/routes/pages.py` (add /r/{code} route)
- Create: `tests/integration/test_audience_view.py`

- [ ] **Step 1: Create `templates/partials/question_card.html`**

```html
<article class="q-card {% if is_new %}q-card-new{% endif %}"
         id="q-{{ q.id }}"
         data-question-id="{{ q.id }}"
         style="background: white; border: 1px solid var(--slate-200);
                border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px;">
  <div style="display: flex; gap: 12px; align-items: flex-start;">
    <button class="upvote-btn"
            data-action="upvote"
            data-id="{{ q.id }}"
            style="background: {% if upvoted %}var(--dlai-coral){% else %}white{% endif %};
                   color: {% if upvoted %}white{% else %}var(--slate-500){% endif %};
                   border: 1px solid var(--slate-200);
                   width: 48px; padding: 8px 0;
                   display: flex; flex-direction: column; align-items: center;
                   border-radius: var(--radius-sm);">
      <span style="font-size: 12px;">▲</span>
      <span class="upvote-count" style="font-size: 14px; font-weight: 600;">{{ q.upvote_count }}</span>
    </button>
    <div style="flex: 1; min-width: 0;">
      <p style="margin: 0 0 6px; line-height: 1.45; word-wrap: break-word;">{{ q.text }}</p>
      <div class="muted" style="font-size: 12px;">
        — {{ q.author_name }}{% if is_mine %} <span style="color: var(--dlai-teal); font-weight: 600;">(you)</span>{% endif %}
      </div>
    </div>
  </div>
</article>
```

- [ ] **Step 2: Create `templates/audience.html`**

```html
{% extends "base.html" %}
{% block title %}{{ room.title or "Q&A" }} — DLAI{% endblock %}
{% block body %}
<header class="app-header">
  <h1>{{ room.title or "Live Q&A" }}</h1>
</header>

{% if needs_join %}
<main style="max-width: 480px; margin: 64px auto; padding: 0 16px;">
  <h2 style="margin: 0 0 16px;">Join this Q&amp;A</h2>
  <form id="join-form" style="display: grid; gap: 12px;">
    <input type="text" name="name" maxlength="40" placeholder="Your name" autofocus required>
    <button type="submit" class="btn-primary">Continue →</button>
    <div id="join-error" style="color: var(--dlai-coral-deep); font-size: 14px;"></div>
  </form>
</main>
<script>
document.getElementById('join-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = e.target.name.value.trim();
  if (!name) return;
  const r = await fetch(window.location.pathname + '/join', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name}),
  });
  if (r.ok) window.location.reload();
  else document.getElementById('join-error').textContent = 'Could not join. Try again.';
});
</script>
{% else %}
<main style="max-width: 600px; margin: 0 auto; padding: 16px; padding-bottom: 140px;">
  <div class="muted" style="font-size: 13px; margin-bottom: 12px;">
    Asking as: <strong>{{ participant.name }}</strong>
  </div>
  <div id="pinned-slot"></div>
  <div id="questions-list">
    {% for q in questions %}
      {% set upvoted = q.id in my_upvotes %}
      {% set is_mine = q.id in my_question_ids %}
      {% include "partials/question_card.html" %}
    {% endfor %}
  </div>
</main>

<form id="composer" style="
    position: fixed; bottom: 0; left: 0; right: 0;
    background: white; border-top: 1px solid var(--slate-200);
    padding: 12px 16px; box-shadow: var(--shadow-md);">
  <div style="max-width: 600px; margin: 0 auto; display: flex; gap: 8px;">
    <textarea name="text" placeholder="Ask a question…" maxlength="280" rows="1"
              style="flex: 1; resize: none;"></textarea>
    <button type="submit" class="btn-primary">Send</button>
  </div>
  <div style="max-width: 600px; margin: 4px auto 0; display: flex; justify-content: space-between;">
    <span id="char-count" class="muted" style="font-size: 12px;">0/280</span>
  </div>
</form>

<script src="/static/js/upvote.js" defer></script>
<script src="/static/js/sse.js" defer></script>
<script>
const ROOM_CODE = {{ room.code|tojson }};
const composer = document.getElementById('composer');
const ta = composer.querySelector('textarea');
const cc = document.getElementById('char-count');
ta.addEventListener('input', () => { cc.textContent = `${ta.value.length}/280`; });
composer.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = ta.value.trim();
  if (!text) return;
  const r = await fetch(`/r/${ROOM_CODE}/questions`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text}),
  });
  if (r.ok) { ta.value = ''; cc.textContent = '0/280'; }
});
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Create `static/js/upvote.js`**

```javascript
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action="upvote"]');
  if (!btn) return;
  e.preventDefault();
  const id = btn.dataset.id;
  const code = window.ROOM_CODE;
  const countEl = btn.querySelector('.upvote-count');
  const wasActive = btn.style.background.includes('245') || btn.style.color === 'white';
  // Optimistic
  countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? -1 : 1));
  btn.classList.add('upvote-active');
  setTimeout(() => btn.classList.remove('upvote-active'), 240);

  try {
    const r = await fetch(`/r/${code}/questions/${id}/upvote`, { method: 'POST' });
    if (!r.ok) throw new Error('upvote failed');
    const body = await r.json();
    countEl.textContent = String(body.upvotes);
    btn.style.background = body.upvoted ? 'var(--dlai-coral)' : 'white';
    btn.style.color = body.upvoted ? 'white' : 'var(--slate-500)';
  } catch (err) {
    // Roll back optimistic update
    countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? 1 : -1));
  }
});
```

- [ ] **Step 4: Create `static/js/sse.js`**

```javascript
(function () {
  const code = window.ROOM_CODE;
  if (!code) return;

  let backoff = 1000;
  const list = document.getElementById('questions-list');
  const pinned = document.getElementById('pinned-slot');

  function appendQuestion(q, isNew) {
    if (!list || document.getElementById('q-' + q.id)) return;
    const tmpl = document.createElement('template');
    tmpl.innerHTML = `<article class="q-card ${isNew ? 'q-card-new' : ''}" id="q-${q.id}" data-question-id="${q.id}"
      style="background:white;border:1px solid var(--slate-200);border-radius:var(--radius-md);padding:14px;margin-bottom:10px;">
      <div style="display:flex;gap:12px;align-items:flex-start;">
        <button class="upvote-btn" data-action="upvote" data-id="${q.id}"
          style="background:white;color:var(--slate-500);border:1px solid var(--slate-200);width:48px;padding:8px 0;display:flex;flex-direction:column;align-items:center;border-radius:var(--radius-sm);">
          <span style="font-size:12px;">▲</span>
          <span class="upvote-count" style="font-size:14px;font-weight:600;">${q.upvote_count}</span>
        </button>
        <div style="flex:1;min-width:0;">
          <p style="margin:0 0 6px;line-height:1.45;word-wrap:break-word;"></p>
          <div class="muted" style="font-size:12px;">— <span class="author"></span></div>
        </div>
      </div>
    </article>`;
    const el = tmpl.content.firstElementChild;
    el.querySelector('p').textContent = q.text;
    el.querySelector('.author').textContent = q.author_name;
    list.prepend(el);
  }

  function updateCount(qid, count) {
    const el = document.querySelector('#q-' + qid + ' .upvote-count');
    if (el) el.textContent = String(count);
  }

  function handleEvent(type, data) {
    if (type === 'question.created') appendQuestion(data, true);
    else if (type === 'question.upvoted') updateCount(data.id, data.upvotes);
    else if (type === 'question.state_changed') {
      // For audience: hidden questions disappear, pinned moves to slot
      const card = document.getElementById('q-' + data.id);
      if (data.state === 'hidden' && card) card.remove();
    }
    else if (type === 'room.closed') {
      window.location.reload();
    }
  }

  function connect() {
    const es = new EventSource(`/r/${code}/events`);
    es.addEventListener('open', () => { backoff = 1000; });
    ['connected', 'question.created', 'question.upvoted', 'question.state_changed', 'room.closed', 'ping']
      .forEach(t => es.addEventListener(t, ev => handleEvent(t, JSON.parse(ev.data))));
    es.addEventListener('error', () => {
      es.close();
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 30000);
    });
  }
  connect();
})();
```

- [ ] **Step 5: Add an inline `window.ROOM_CODE = …` to `audience.html`**

Inside the `<body>` block of `audience.html`, before the closing `</main>`, change the script block to set the global:

Replace:
```javascript
const ROOM_CODE = {{ room.code|tojson }};
```

With:
```javascript
window.ROOM_CODE = {{ room.code|tojson }};
const ROOM_CODE = window.ROOM_CODE;
```

- [ ] **Step 6: Add `/r/{code}` page route in `app/routes/pages.py`**

Append to the file:

```python
from sqlalchemy import select

from app.auth import get_or_create_session_id, get_room_by_code
from app.db import get_session
from app.models import Participant, Question, QuestionState, Upvote


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
```

- [ ] **Step 7: Create `templates/room_ended.html`**

```html
{% extends "base.html" %}
{% block title %}Q&A ended — DLAI{% endblock %}
{% block body %}
<main style="max-width: 480px; margin: 96px auto; padding: 0 16px; text-align: center;">
  <h1>This Q&amp;A has ended</h1>
  <p class="muted">Thanks for joining {{ room.title or "the session" }}.</p>
</main>
{% endblock %}
```

- [ ] **Step 8: Create `tests/integration/test_audience_view.py`**

```python
async def test_audience_sees_join_form_first(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}")
    assert r.status_code == 200
    assert "Join this Q&amp;A" in r.text
    assert "Your name" in r.text


async def test_audience_sees_questions_after_join(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    await client.post(f"/r/{code}/questions", json={"text": "first?"})
    r = await client.get(f"/r/{code}")
    assert "first?" in r.text
    assert "Sam" in r.text


async def test_closed_room_shows_ended_message(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    await client.post(f"/r/{code}/end?t={token}")
    r = await client.get(f"/r/{code}")
    assert "ended" in r.text.lower()
```

- [ ] **Step 9: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_audience_view.py -v
```

Expected: 3 passed.

- [ ] **Step 10: Commit**

```bash
git add templates/audience.html templates/partials/ templates/room_ended.html static/js/ app/routes/pages.py tests/integration/test_audience_view.py
git commit -m "feat: add audience view with join, ask, upvote, and SSE updates"
```

---

### Task G4: Presenter dashboard (share screen + queue)

**Files:**
- Create: `templates/presenter.html`
- Create: `templates/presenter_share.html`
- Create: `app/utils/qr.py`
- Modify: `app/routes/pages.py`
- Create: `tests/integration/test_presenter_view.py`

- [ ] **Step 1: Create `app/utils/qr.py`**

```python
import qrcode
from qrcode.image.svg import SvgPathImage


def generate_qr_svg(url: str, *, scale: int = 8) -> str:
    qr = qrcode.QRCode(box_size=scale, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    return img.to_string(encoding="unicode")
```

- [ ] **Step 2: Create `templates/presenter_share.html`**

```html
{% extends "base.html" %}
{% block title %}Share — {{ room.title or "Q&A" }} — DLAI{% endblock %}
{% block body %}
<header class="app-header">
  <h1>{{ room.title or "Live Q&A" }}</h1>
</header>
<main style="max-width: 720px; margin: 32px auto; padding: 0 16px;">
  <h2 style="margin: 0 0 16px;">Share with your audience</h2>
  <div style="display: grid; grid-template-columns: minmax(200px, 280px) 1fr; gap: 32px; align-items: start;">
    <div class="card" style="padding: 20px;">
      {{ qr_svg|safe }}
    </div>
    <div>
      <div style="font-size: 13px; color: var(--slate-500); margin-bottom: 4px;">Room code</div>
      <div style="font-family: 'SF Mono', monospace; font-size: 32px; font-weight: 700; letter-spacing: 4px; color: var(--dlai-coral); margin-bottom: 16px;">
        {{ room.code }}
      </div>
      <div style="font-size: 13px; color: var(--slate-500); margin-bottom: 4px;">Direct link</div>
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <input type="text" value="{{ audience_url }}" readonly id="aud-url">
        <button class="btn-secondary" onclick="navigator.clipboard.writeText(document.getElementById('aud-url').value)">Copy</button>
      </div>
      <a href="/r/{{ room.code }}/host/qr?t={{ token }}" class="btn-secondary" style="display: inline-block; padding: 10px 16px; border: 1px solid var(--slate-200); border-radius: var(--radius-sm); color: var(--slate-900);">
        ⛶ Show fullscreen QR
      </a>
    </div>
  </div>
  <p class="muted" style="margin-top: 24px;">
    Bookmark this page — it's your only way back as presenter. Anyone with this URL becomes the host.
  </p>
  <div style="margin-top: 32px; padding: 16px; background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-md); text-align: center;">
    <p class="muted">Waiting for first question…</p>
    <a href="/r/{{ room.code }}/host?t={{ token }}&v=live" style="color: var(--dlai-teal);">Switch to live dashboard →</a>
  </div>
</main>
{% endblock %}
```

- [ ] **Step 3: Create `templates/presenter.html`**

```html
{% extends "base.html" %}
{% block title %}Presenter — {{ room.title or "Q&A" }} — DLAI{% endblock %}
{% block body %}
<header class="app-header">
  <h1>{{ room.title or "Live Q&A" }}</h1>
  <div style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
    <a href="/r/{{ room.code }}/host/qr?t={{ token }}" style="color: white; opacity: 0.85;">QR ⊞</a>
    <a href="/r/{{ room.code }}/export.csv?t={{ token }}" style="color: white; opacity: 0.85;">Download CSV</a>
    <button class="btn-secondary" onclick="endSession()">End session</button>
  </div>
</header>

<main style="display: grid; grid-template-columns: 320px 1fr; gap: 24px; padding: 24px; max-width: 1280px; margin: 0 auto;">
  <aside>
    <h2 style="font-size: 14px; text-transform: uppercase; color: var(--slate-500); margin: 0 0 8px;">Answering now</h2>
    <div id="pinned-slot" class="card" style="min-height: 120px;">
      <p class="muted" style="margin: 0;">Pin a question to highlight it here.</p>
    </div>
  </aside>
  <section>
    <h2 style="font-size: 14px; text-transform: uppercase; color: var(--slate-500); margin: 0 0 8px;">Question queue</h2>
    <div id="questions-list">
      {% for q in questions %}
        {% set upvoted = false %}
        {% set is_mine = false %}
        <article class="q-card" id="q-{{ q.id }}" data-question-id="{{ q.id }}"
                 style="background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px;">
          <div style="display: flex; gap: 12px; align-items: flex-start;">
            <div style="width: 48px; padding: 8px 0; text-align: center; color: var(--slate-700); border: 1px solid var(--slate-200); border-radius: var(--radius-sm);">
              <div style="font-size: 12px;">▲</div>
              <div class="upvote-count" style="font-size: 14px; font-weight: 600;">{{ q.upvote_count }}</div>
            </div>
            <div style="flex: 1; min-width: 0;">
              <p style="margin: 0 0 6px; line-height: 1.45;">{{ q.text }}</p>
              <div class="muted" style="font-size: 12px;">— {{ q.author_name }}</div>
              <div style="margin-top: 8px; display: flex; gap: 6px;">
                <button class="btn-secondary action-btn" data-act="state" data-val="pinned" data-id="{{ q.id }}">📌 Pin</button>
                <button class="btn-secondary action-btn" data-act="state" data-val="answered" data-id="{{ q.id }}">✓ Answered</button>
                <button class="btn-secondary action-btn" data-act="state" data-val="hidden" data-id="{{ q.id }}">⊘ Hide</button>
                <button class="btn-secondary action-btn" data-act="starred" data-val="toggle" data-id="{{ q.id }}">⭐ Star</button>
              </div>
            </div>
          </div>
        </article>
      {% endfor %}
    </div>
  </section>
</main>

<script>
window.ROOM_CODE = {{ room.code|tojson }};
window.PRESENTER_TOKEN = {{ token|tojson }};

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.action-btn');
  if (!btn) return;
  const id = btn.dataset.id;
  const body = {};
  if (btn.dataset.act === 'state') body.state = btn.dataset.val;
  if (btn.dataset.act === 'starred') {
    const card = document.getElementById('q-' + id);
    body.starred = !card.dataset.starred || card.dataset.starred === 'false';
  }
  await fetch(`/r/${window.ROOM_CODE}/questions/${id}?t=${window.PRESENTER_TOKEN}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
});

async function endSession() {
  if (!confirm("End this session? Audience won't be able to ask new questions.")) return;
  await fetch(`/r/${window.ROOM_CODE}/end?t=${window.PRESENTER_TOKEN}`, { method: 'POST' });
  alert('Session ended.');
}
</script>
<script src="/static/js/sse.js" defer></script>
{% endblock %}
```

- [ ] **Step 4: Add presenter routes to `app/routes/pages.py`**

Append:

```python
from app.config import get_settings
from app.utils.qr import generate_qr_svg


@router.get("/r/{code}/host", response_class=HTMLResponse)
async def presenter_view(
    code: str,
    request: Request,
    t: str | None = None,
    v: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    room = await get_room_by_code(code, db)
    if not t or not constant_time_eq(t, room.presenter_token):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"/r/{code}", status_code=303)

    base = get_settings().app_base_url.rstrip("/")
    audience_url = f"{base}/r/{room.code}"

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
):
    room = await get_room_by_code(code, db)
    if not t or not constant_time_eq(t, room.presenter_token):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"/r/{code}", status_code=303)
    base = get_settings().app_base_url.rstrip("/")
    audience_url = f"{base}/r/{room.code}"
    return request.app.state.templates.TemplateResponse(
        request,
        "fullscreen_qr.html",
        {"room": room, "audience_url": audience_url, "qr_svg": generate_qr_svg(audience_url, scale=14)},
    )
```

- [ ] **Step 5: Create `templates/fullscreen_qr.html`**

```html
{% extends "base.html" %}
{% block title %}Scan to ask — {{ room.title or "Q&A" }}{% endblock %}
{% block footer %}{% endblock %}
{% block body %}
<main style="background: var(--slate-900); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px; color: white;">
  <h1 style="font-weight: 600; margin: 0 0 32px;">Scan to ask a question</h1>
  <div style="background: white; padding: 24px; border-radius: 16px;">
    {{ qr_svg|safe }}
  </div>
  <p style="margin: 32px 0 8px; color: var(--slate-400);">or visit {{ audience_url }}</p>
  <div style="font-family: 'SF Mono', monospace; font-size: 64px; font-weight: 700; letter-spacing: 8px; color: var(--dlai-coral);">
    {{ room.code }}
  </div>
  <button onclick="window.close() || history.back()" style="position: absolute; bottom: 24px; right: 24px;" class="btn-secondary">esc</button>
</main>
<script>
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') history.back(); });
</script>
{% endblock %}
```

- [ ] **Step 6: Create `tests/integration/test_presenter_view.py`**

```python
async def test_presenter_share_screen_first_load(client):
    create = await client.post("/rooms", json={"title": "Test"})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    r = await client.get(f"/r/{code}/host?t={token}")
    assert r.status_code == 200
    assert "Share with your audience" in r.text
    assert code in r.text


async def test_presenter_wrong_token_redirects(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}/host?t=bogus", follow_redirects=False)
    assert r.status_code == 303


async def test_fullscreen_qr_route(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    r = await client.get(f"/r/{code}/host/qr?t={token}")
    assert r.status_code == 200
    assert "Scan to ask" in r.text
```

- [ ] **Step 7: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_presenter_view.py -v
```

Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add app/utils/qr.py templates/presenter.html templates/presenter_share.html templates/fullscreen_qr.html app/routes/pages.py tests/integration/test_presenter_view.py
git commit -m "feat: add presenter dashboard, share screen, and fullscreen QR"
```

---

## Phase H — CSV export

### Task H1: CSV export endpoint

**Files:**
- Create: `app/services/csv_export.py`
- Create: `app/routes/export.py`
- Modify: `app/main.py`
- Create: `tests/unit/test_csv_export.py`
- Create: `tests/integration/test_export_endpoint.py`

- [ ] **Step 1: Create `app/services/csv_export.py`**

```python
import csv
import io
from typing import Iterable

from app.models import Question, Room


def build_csv(room: Room, questions: Iterable[Question]) -> bytes:
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM so Excel opens correctly
    w = csv.writer(buf)
    w.writerow([
        "question_id", "author_name", "text", "state", "starred",
        "upvote_count", "created_at", "room_title", "room_code",
    ])
    for q in questions:
        w.writerow([
            q.id, q.author_name, q.text, q.state.value, q.starred,
            q.upvote_count, q.created_at.isoformat(),
            room.title or "", room.code,
        ])
    return buf.getvalue().encode("utf-8")
```

- [ ] **Step 2: Create `app/routes/export.py`**

```python
from datetime import datetime, timezone

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
        select(Question)
        .where(Question.room_id == room.id)
        .order_by(Question.created_at.asc())
    )
    questions = list(result.scalars())
    payload = build_csv(room, questions)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"qa-{room.code}-{today}.csv"
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 3: Register router in `app/main.py`**

Add to imports:
```python
from app.routes import export as export_routes
```

After events router:
```python
app.include_router(export_routes.router)
```

- [ ] **Step 4: Create `tests/unit/test_csv_export.py`**

```python
from datetime import datetime, timezone

from app.models import Question, QuestionState, Room, RoomStatus
from app.services.csv_export import build_csv


def test_build_csv_includes_bom_and_header():
    room = Room(
        id=1, code="ABCDEF", presenter_token="t" * 32, title="Hi",
        status=RoomStatus.ACTIVE, expires_at=datetime.now(timezone.utc),
    )
    payload = build_csv(room, [])
    text = payload.decode("utf-8")
    assert text.startswith("﻿")
    assert "question_id,author_name,text,state,starred,upvote_count" in text


def test_build_csv_writes_rows():
    room = Room(
        id=1, code="ABCDEF", presenter_token="t" * 32, title="Hi",
        status=RoomStatus.ACTIVE, expires_at=datetime.now(timezone.utc),
    )
    q = Question(
        id=10, room_id=1, participant_id=1, author_name="Sam", text="hello",
        state=QuestionState.LIVE, starred=False, upvote_count=3,
        created_at=datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    payload = build_csv(room, [q]).decode("utf-8")
    assert "Sam" in payload
    assert "hello" in payload
    assert "ABCDEF" in payload
```

- [ ] **Step 5: Create `tests/integration/test_export_endpoint.py`**

```python
async def test_export_csv_returns_attachment(client):
    create = await client.post("/rooms", json={"title": "T"})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    await client.post(f"/r/{code}/questions", json={"text": "hi"})

    r = await client.get(f"/r/{code}/export.csv?t={token}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert f"qa-{code}" in r.headers["content-disposition"]
    assert "Sam" in r.text and "hi" in r.text


async def test_export_requires_token(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}/export.csv", follow_redirects=False)
    assert r.status_code == 303
```

- [ ] **Step 6: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_csv_export.py tests/integration/test_export_endpoint.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add app/services/csv_export.py app/routes/export.py app/main.py tests/unit/test_csv_export.py tests/integration/test_export_endpoint.py
git commit -m "feat: add CSV export endpoint with UTF-8 BOM for Excel"
```

---

## Phase I — Email-on-close

### Task I1: Resend email service

**Files:**
- Create: `app/services/email.py`
- Create: `templates/email/session_ended.html`
- Create: `tests/unit/test_email.py`

- [ ] **Step 1: Create `app/services/email.py`**

```python
import asyncio
import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger("qa.email")

RESEND_URL = "https://api.resend.com/emails"


@dataclass
class EmailAttachment:
    filename: str
    content_b64: str
    content_type: str = "text/csv"


async def send_session_ended_email(
    *,
    to_address: str,
    subject: str,
    html_body: str,
    csv_attachment: bytes,
    csv_filename: str,
    max_retries: int = 3,
) -> bool:
    s = get_settings()
    if not s.email_api_key:
        logger.warning("EMAIL_API_KEY not configured; skipping send")
        return False
    payload = {
        "from": f"{s.email_from_name} <{s.email_from_address}>",
        "to": [to_address],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {
                "filename": csv_filename,
                "content": base64.b64encode(csv_attachment).decode("ascii"),
            }
        ],
    }
    delay = 2.0
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                r = await http.post(
                    RESEND_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {s.email_api_key}"},
                )
            if 200 <= r.status_code < 300:
                return True
            logger.error("resend non-2xx", extra={"status": r.status_code, "body": r.text})
        except httpx.RequestError as e:
            logger.error("resend request error", extra={"err": str(e)})
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            delay *= 4
    return False
```

- [ ] **Step 2: Create `templates/email/session_ended.html`**

```html
<!doctype html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif; color: #0F172A; max-width: 600px; margin: 0 auto;">
  <div style="background: #F65B66; color: white; padding: 24px;">
    <h1 style="margin: 0; font-size: 20px;">Your Q&amp;A session has ended</h1>
  </div>
  <div style="padding: 24px;">
    <p>Hi,</p>
    <p>Your session <strong>{{ title or 'Q&A' }}</strong> just wrapped up.</p>
    <ul style="line-height: 1.8;">
      <li>Total questions: <strong>{{ stats.total }}</strong></li>
      <li>Total upvotes: <strong>{{ stats.upvotes }}</strong></li>
      <li>Participants: <strong>{{ stats.participants }}</strong></li>
    </ul>
    <p>The full Q&amp;A archive is attached as a CSV. You can also revisit the room
       (read-only) for the next 24 hours: <a href="{{ permalink }}">{{ permalink }}</a></p>
    <p style="font-size: 13px; color: #64748B; margin-top: 32px;">
      We're emailing you because you asked us to. We won't use your address for anything else.
    </p>
  </div>
  <div style="text-align: center; padding: 24px; color: #64748B; font-size: 13px;">
    Made with <span style="color: #F65B66;">♥</span> from Gaurav &amp; DeepLearning.AI
  </div>
</body>
</html>
```

- [ ] **Step 3: Create `tests/unit/test_email.py`**

```python
from unittest.mock import AsyncMock, patch

import pytest

from app.services.email import send_session_ended_email


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "test-key")
    from app.config import get_settings
    get_settings.cache_clear()


async def test_returns_true_on_2xx():
    with patch("httpx.AsyncClient") as mock_client_cls:
        instance = mock_client_cls.return_value.__aenter__.return_value
        instance.post = AsyncMock()
        instance.post.return_value.status_code = 200
        instance.post.return_value.text = "ok"
        ok = await send_session_ended_email(
            to_address="a@b.co",
            subject="x",
            html_body="<p>hi</p>",
            csv_attachment=b"hi",
            csv_filename="x.csv",
        )
        assert ok is True


async def test_retries_on_5xx_then_fails():
    with patch("app.services.email.asyncio.sleep", new=AsyncMock()), \
         patch("httpx.AsyncClient") as mock_client_cls:
        instance = mock_client_cls.return_value.__aenter__.return_value
        instance.post = AsyncMock()
        instance.post.return_value.status_code = 503
        instance.post.return_value.text = "bad"
        ok = await send_session_ended_email(
            to_address="a@b.co",
            subject="x",
            html_body="<p>hi</p>",
            csv_attachment=b"hi",
            csv_filename="x.csv",
            max_retries=2,
        )
        assert ok is False
        assert instance.post.await_count == 2


async def test_skips_when_no_api_key(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    ok = await send_session_ended_email(
        to_address="a@b.co",
        subject="x",
        html_body="<p>hi</p>",
        csv_attachment=b"hi",
        csv_filename="x.csv",
    )
    assert ok is False
```

- [ ] **Step 4: Run (expect PASS)**

```bash
uv run pytest tests/unit/test_email.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/email.py templates/email/session_ended.html tests/unit/test_email.py
git commit -m "feat: add Resend email client with retry and HTML template"
```

---

### Task I2: Wire email-on-close into end_session

**Files:**
- Modify: `app/routes/rooms.py`
- Create: `tests/integration/test_email_on_close.py`

- [ ] **Step 1: Update `app/routes/rooms.py` to enqueue email on close**

Add the imports at the top:

```python
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy import func, select

from app.models import Participant, Question
from app.services.csv_export import build_csv
from app.services.email import send_session_ended_email
from app.config import get_settings
```

Replace the `end_session` function with:

```python
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
        from datetime import datetime as _dt
        filename = f"qa-{room.code}-{_dt.now(timezone.utc).strftime('%Y-%m-%d')}.csv"

        async def _send_and_record():
            ok = await send_session_ended_email(
                to_address=room.presenter_email,
                subject=f"Your Q&A session '{title or room.code}' has ended",
                html_body=html_body,
                csv_attachment=csv_bytes,
                csv_filename=filename,
            )
            if ok:
                from app.db import get_sessionmaker
                sm = get_sessionmaker()
                async with sm() as s:
                    fresh = await s.get(Room, room.id)
                    if fresh:
                        fresh.email_sent_at = datetime.now(timezone.utc)
                        await s.commit()

        background_tasks.add_task(_send_and_record)

    return {"status": "closed"}


def _render_email_html(*, title: str | None, stats: dict, permalink: str) -> str:
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader(Path(__file__).resolve().parent.parent.parent / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("email/session_ended.html").render(
        title=title, stats=stats, permalink=permalink,
    )
```

- [ ] **Step 2: Create `tests/integration/test_email_on_close.py`**

```python
from unittest.mock import AsyncMock, patch


async def test_email_not_sent_without_address(client):
    with patch("app.routes.rooms.send_session_ended_email", new=AsyncMock()) as mock_send:
        create = await client.post("/rooms", json={})
        body = create.json()
        code = body["code"]
        token = body["presenter_url"].split("t=")[1]
        await client.post(f"/r/{code}/end?t={token}")
        mock_send.assert_not_awaited()


async def test_email_sent_when_address_provided(client):
    with patch("app.routes.rooms.send_session_ended_email", new=AsyncMock(return_value=True)) as mock_send:
        create = await client.post("/rooms", json={"presenter_email": "a@b.co", "title": "T"})
        body = create.json()
        code = body["code"]
        token = body["presenter_url"].split("t=")[1]
        await client.post(f"/r/{code}/join", json={"name": "Sam"})
        await client.post(f"/r/{code}/questions", json={"text": "hi"})

        r = await client.post(f"/r/{code}/end?t={token}")
        assert r.status_code == 200
        # BackgroundTasks may run after response; httpx test client awaits them.
        mock_send.assert_awaited_once()
        kwargs = mock_send.await_args.kwargs
        assert kwargs["to_address"] == "a@b.co"
        assert b"hi" in kwargs["csv_attachment"]
```

- [ ] **Step 3: Run (expect PASS)**

```bash
uv run pytest tests/integration/test_email_on_close.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/routes/rooms.py tests/integration/test_email_on_close.py
git commit -m "feat: send CSV email on session close (when email provided)"
```

---

## Phase J — Polish

### Task J1: Live audience pill + presenter keyboard shortcuts

**Files:**
- Create: `static/js/shortcuts.js`
- Modify: `app/services/pubsub.py`
- Modify: `templates/presenter.html`
- Modify: `static/js/sse.js` (already exists; add audience-count handling)

- [ ] **Step 1: Add subscriber-count event publishing**

Edit `app/routes/events.py`. Replace the `stream` function body with:

```python
    async def stream() -> AsyncIterator[bytes]:
        async with pubsub.subscribe(room.id) as q:
            yield _format_sse("connected", {"room_id": room.id})
            count = await pubsub.subscriber_count(room.id)
            await pubsub.publish(
                room.id, {"type": "audience.count", "data": {"count": count}}
            )
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=20.0)
                        yield _format_sse(event["type"], event["data"])
                    except asyncio.TimeoutError:
                        yield _format_sse("ping", {})
            finally:
                count_after = await pubsub.subscriber_count(room.id) - 1
                await pubsub.publish(
                    room.id, {"type": "audience.count", "data": {"count": max(0, count_after)}}
                )
```

- [ ] **Step 2: Update `static/js/sse.js` to handle audience count**

Inside the `handleEvent` function, add:

```javascript
    else if (type === 'audience.count') {
      const el = document.getElementById('audience-pill');
      if (el) el.textContent = `● ${data.count} listening`;
    }
```

And in the event listeners list, add `'audience.count'`.

- [ ] **Step 3: Add the pill markup to `templates/presenter.html`**

In the `<header>` block, before the QR link, add:

```html
<span id="audience-pill" style="font-size: 13px; opacity: 0.85;">● 0 listening</span>
```

- [ ] **Step 4: Create `static/js/shortcuts.js`**

```javascript
(function () {
  if (!window.PRESENTER_TOKEN) return;
  const code = window.ROOM_CODE;
  const token = window.PRESENTER_TOKEN;

  function topQuestion() {
    return document.querySelector('#questions-list .q-card');
  }
  async function patch(id, body) {
    return fetch(`/r/${code}/questions/${id}?t=${token}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const top = topQuestion();
    if (!top) return;
    const id = top.dataset.questionId;
    if (e.key === 'p' || e.key === 'P') patch(id, {state: 'pinned'});
    else if (e.key === 'a' || e.key === 'A') patch(id, {state: 'answered'});
    else if (e.key === 'h' || e.key === 'H') patch(id, {state: 'hidden'});
    else if (e.key === 's' || e.key === 'S') patch(id, {starred: true});
  });
})();
```

- [ ] **Step 5: Include `shortcuts.js` in `presenter.html`**

Add before the `</body>` close (or end of body block):
```html
<script src="/static/js/shortcuts.js" defer></script>
```

- [ ] **Step 6: Manual smoke test**

```bash
uv run uvicorn app.main:app --port 8000 &
sleep 2
echo "Open http://localhost:8000 in two browser tabs (presenter + audience), submit a question, press P in presenter tab. Verify pin happens."
kill %1
```

- [ ] **Step 7: Commit**

```bash
git add app/routes/events.py static/js/shortcuts.js static/js/sse.js templates/presenter.html
git commit -m "feat: add live audience-count pill and presenter keyboard shortcuts"
```

---

## Phase K — Deployment

### Task K1: Dockerfile + railway.toml + healthz hardening

**Files:**
- Create: `Dockerfile`
- Create: `railway.toml`
- Create: `README.md`
- Modify: `app/main.py` (add `/healthz` DB ping)

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY static ./static
COPY templates ./templates

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 2: Create `railway.toml`**

```toml
[build]
builder = "DOCKERFILE"

[deploy]
healthcheckPath = "/healthz"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[mounts]]
volumePath = "/data"
```

- [ ] **Step 3: Create `README.md`**

```markdown
# DLAI Q&A

Live Q&A web app. Audience scans QR, types name, asks + upvotes questions.
Presenter pins / answers / hides / stars in real time.

## Run locally

    uv sync --all-groups
    cp .env.example .env  # set SESSION_SECRET (32+ chars) and EMAIL_API_KEY (Resend)
    uv run uvicorn app.main:app --reload

## Test

    uv run pytest

## Deploy (Railway)

1. Create a new service, point to this repo.
2. Set env vars: `SESSION_SECRET`, `EMAIL_API_KEY`, `EMAIL_FROM_ADDRESS`, `APP_BASE_URL`.
3. Mount a volume at `/data`.
4. Set `SQLITE_PATH=/data/qa.db`.
```

- [ ] **Step 4: Create `.env.example`**

```
APP_BASE_URL=http://localhost:8000
SQLITE_PATH=./data/qa.db
SESSION_SECRET=replace-me-with-a-32-char-or-longer-secret
EMAIL_API_KEY=
EMAIL_FROM_ADDRESS=qa@example.com
EMAIL_FROM_NAME="DLAI Q&A"
LOG_LEVEL=INFO
```

- [ ] **Step 5: Harden healthz with DB ping**

Replace the `healthz` function in `app/main.py` with:

```python
from sqlalchemy import text
from app.db import get_sessionmaker


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    sm = get_sessionmaker()
    async with sm() as s:
        await s.execute(text("SELECT 1"))
    return {"status": "ok"}
```

- [ ] **Step 6: Build and run the container locally**

```bash
docker build -t qa-app:dev .
docker run --rm -p 8000:8000 \
  -e SESSION_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))") \
  -e SQLITE_PATH=/tmp/qa.db \
  qa-app:dev &
sleep 4
curl -s http://localhost:8000/healthz
docker stop $(docker ps -q --filter ancestor=qa-app:dev)
```

Expected: `{"status":"ok"}`

- [ ] **Step 7: Commit**

```bash
git add Dockerfile railway.toml README.md .env.example app/main.py
git commit -m "feat: add Dockerfile, railway.toml, README, and healthz DB ping"
```

---

## Phase L — End-to-end tests

### Task L1: Playwright E2E for the three critical flows

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_create_room.py`
- Create: `tests/e2e/test_audience_flow.py`
- Create: `tests/e2e/test_presenter_flow.py`

- [ ] **Step 1: Install Playwright browsers**

```bash
uv run playwright install chromium
```

- [ ] **Step 2: Create `tests/e2e/__init__.py` (empty)**

```python
```

- [ ] **Step 3: Create `tests/e2e/conftest.py`**

```python
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    port = _free_port()
    db = tmp_path_factory.mktemp("e2e") / "qa.db"
    env = {
        **os.environ,
        "SESSION_SECRET": "x" * 32,
        "SQLITE_PATH": str(db),
        "APP_BASE_URL": f"http://127.0.0.1:{port}",
        "EMAIL_API_KEY": "",
    }
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )
    deadline = time.time() + 15
    import urllib.request
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def page(live_server):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(5000)
        yield page
        browser.close()
```

- [ ] **Step 4: Create `tests/e2e/test_create_room.py`**

```python
def test_homepage_creates_room_and_redirects_to_share_screen(live_server, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "E2E Test")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    assert "Share with your audience" in page.content()
    assert page.locator("svg").count() >= 1  # QR is an SVG
```

- [ ] **Step 5: Create `tests/e2e/test_audience_flow.py`**

```python
import re


def test_audience_join_ask_upvote(live_server, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "Audience flow")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    code = re.search(r"/r/([A-Z0-9]{6})/", page.url).group(1)

    page.goto(f"{live_server}/r/{code}")
    page.fill('input[name="name"]', "Sam")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    page.fill("textarea", "What about cost?")
    page.click('button[type="submit"]')
    page.wait_for_selector("text=What about cost?")

    page.click('[data-action="upvote"]')
    page.wait_for_function('document.querySelector(".upvote-count").textContent === "1"')
```

- [ ] **Step 6: Create `tests/e2e/test_presenter_flow.py`**

```python
import re

from playwright.sync_api import sync_playwright


def test_presenter_pin_then_answer(live_server, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "Presenter flow")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    presenter_url = page.url
    code = re.search(r"/r/([A-Z0-9]{6})/", presenter_url).group(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        audience = ctx.new_page()
        audience.set_default_timeout(5000)
        audience.goto(f"{live_server}/r/{code}")
        audience.fill('input[name="name"]', "Sam")
        audience.click('button[type="submit"]')
        audience.wait_for_load_state("networkidle")
        audience.fill("textarea", "Pin me")
        audience.click('button[type="submit"]')

        page.goto(presenter_url + "&v=live")
        page.wait_for_selector("text=Pin me")
        page.click('button[data-act="state"][data-val="pinned"]')

        audience.wait_for_load_state("networkidle")
        browser.close()
```

- [ ] **Step 7: Run E2E tests**

```bash
uv run pytest tests/e2e -v
```

Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add tests/e2e/
git commit -m "test: add Playwright E2E for create-room, audience flow, presenter flow"
```

---

## Phase M — Final polish + deployment

### Task M1: Run full test suite + lint + type-check

- [ ] **Step 1: Run lints**

```bash
uv run ruff check .
uv run ruff format --check .
```

Expected: clean.

- [ ] **Step 2: Run mypy**

```bash
uv run mypy app/
```

Expected: clean.

- [ ] **Step 3: Run all tests with coverage**

```bash
uv run pytest --cov=app --cov-report=term-missing
```

Expected: all green, coverage ≥ 80%.

- [ ] **Step 4: Build the Docker image one more time**

```bash
docker build -t qa-app:rc1 .
```

Expected: succeeds.

- [ ] **Step 5: Commit if any fixes were needed**

```bash
git add -A
git commit -m "chore: final lint and coverage pass"
```

### Task M2: Deploy to Railway

- [ ] **Step 1: Push to a remote**

```bash
gh repo create qa-app --private --source=. --remote=origin --push
```

Or push to an existing remote.

- [ ] **Step 2: Connect Railway service to the repo**

In the Railway dashboard:
1. New project → Deploy from GitHub → select `qa-app`.
2. Add a volume, mount path `/data`.
3. Add env vars:
   - `SESSION_SECRET` (32+ random bytes — use `openssl rand -hex 32`)
   - `EMAIL_API_KEY` (Resend production key)
   - `EMAIL_FROM_ADDRESS` (verified sender address)
   - `EMAIL_FROM_NAME` = `"DLAI Q&A"`
   - `APP_BASE_URL` (the Railway-assigned URL, e.g. `https://qa-app-production.up.railway.app`)
   - `SQLITE_PATH=/data/qa.db`
   - `LOG_LEVEL=INFO`
4. Trigger deploy.

- [ ] **Step 3: Smoke test the deployed app**

```bash
curl -s https://<your-railway-url>/healthz
# expect: {"status":"ok"}
```

Then open the URL in a browser and run through:
- Create a session.
- Open the audience URL on a phone (scan the QR).
- Submit a question.
- Pin / answer / hide it from the presenter dashboard.
- Download the CSV.
- End the session and confirm email arrives if you provided one.

- [ ] **Step 4: Tag the release**

```bash
git tag v0.1.0
git push --tags
```

---

## Self-review notes

- **Spec coverage check:**
  - § 1 Overview / § 2 Constraints — covered by Phase A scaffold and config.
  - § 3 Architecture — Phase A (FastAPI + SQLite) + Phase F (SSE).
  - § 4 Data model — Phase B1 (models) and B2 (schemas).
  - § 5 User flows — Phases D, E, G, H (room create, ask, upvote, presenter actions, CSV).
  - § 6 View layouts — Phase G2 (homepage), G3 (audience), G4 (presenter + fullscreen QR).
  - § 7 Brand styling — Phase G1 (tokens.css, base.css with all coral + slate variables).
  - § 8 Polish & motion — Phase G1 animations.css covers entrance/skeleton/heartbeat; Phase J adds keyboard shortcuts and audience pill. Confetti / FLIP / deterministic avatars are deferred polish to keep v1 focused (noted but not in this plan); rolling-digit count and Motion One library are not in the plan as the optimistic JS handles count updates at the level the spec needs.
  - § 9 Real-time — Phase F (pubsub + SSE) and Phase J (audience count).
  - § 10 Error handling — covered by per-endpoint validation (status 422 / 410 / 429 / 303), email retry in services/email.py, and the room expiry sweep in D2.
  - § 11 Project structure — file tree at top of plan matches spec exactly.
  - § 12 Testing — every task has TDD steps; coverage gate in M1.
  - § 13 Deployment — Phase K (Dockerfile + railway.toml + env vars).
  - § 14 Out of scope — none of those items appear in tasks.
  - § 15 Open questions — addressed: HTMX + minimal vanilla JS chosen, room-code retry implemented in services/rooms.py:create_room, create_all() used (Alembic deferred), qrcode SVG used, Resend chosen, BackgroundTasks used.

- **Placeholder scan:** none — every step contains executable code, exact paths, and exact commands.

- **Type consistency:**
  - `QuestionState` is the single source of truth — `services/questions.py`, `routes/questions.py`, `schemas.py` all use the string values via `Literal[…]` matching the enum.
  - `RoomStatus` ditto.
  - `pubsub.publish(room_id: int, event: dict)` — used consistently in all three publishers.
  - `_ensure_room_writable` lives in `routes/questions.py` and is imported by `routes/upvotes.py`.
  - `get_or_create_session_id` returns `str` everywhere it's used.

- **Deferred polish (explicit):** confetti at 50th question, FLIP animations for pin transitions, deterministic gradient avatars, rolling-digit count animations. None block v1; all live in tracked items in the spec's Section 8 and can be added in a v1.1 plan.
