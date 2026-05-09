import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, text

from app import models
from app.config import get_settings
from app.db import create_all, dispose_engine, get_sessionmaker, init_engine
from app.routes import events as events_routes
from app.routes import export as export_routes
from app.routes import pages as pages_routes
from app.routes import questions as questions_routes
from app.routes import rooms as rooms_routes
from app.routes import upvotes as upvotes_routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_settings()
    init_engine()
    await create_all()
    sweep_task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()
        try:
            await sweep_task
        except asyncio.CancelledError:
            pass
        await dispose_engine()


_sweep_logger = logging.getLogger("qa.sweep")


async def _sweep_loop() -> None:
    while True:
        try:
            sm = get_sessionmaker()
            async with sm() as s:
                await s.execute(
                    delete(models.Room).where(models.Room.expires_at < datetime.now(UTC))
                )
                await s.commit()
        except Exception:
            _sweep_logger.exception("expiry sweep failed")
        await asyncio.sleep(600)


app = FastAPI(title="AskUp", lifespan=lifespan)

_BASE = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")
templates = Jinja2Templates(directory=_BASE / "templates")
app.state.templates = templates

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    sm = get_sessionmaker()
    async with sm() as s:
        await s.execute(text("SELECT 1"))
    return {"status": "ok"}


# Order matters: rooms/questions/upvotes/events/export define explicit prefixes
# that won't conflict with the catch-all `/{code}` registered at the end of pages_routes.
app.include_router(rooms_routes.router)
app.include_router(questions_routes.router)
app.include_router(upvotes_routes.router)
app.include_router(events_routes.router)
app.include_router(export_routes.router)
app.include_router(pages_routes.router)
