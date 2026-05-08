import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, text

from app.config import get_settings
from app.db import create_all, dispose_engine, get_sessionmaker, init_engine
from app import models  # noqa: F401  (registers tables with Base.metadata)
from app.routes import events as events_routes
from app.routes import export as export_routes
from app.routes import pages as pages_routes
from app.routes import rooms as rooms_routes
from app.routes import questions as questions_routes
from app.routes import upvotes as upvotes_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
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


async def _sweep_loop() -> None:
    while True:
        try:
            sm = get_sessionmaker()
            async with sm() as s:
                await s.execute(
                    delete(models.Room).where(models.Room.expires_at < datetime.now(timezone.utc))
                )
                await s.commit()
        except Exception:
            pass
        await asyncio.sleep(600)


app = FastAPI(title="qa-app", lifespan=lifespan)

_BASE = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")
templates = Jinja2Templates(directory=_BASE / "templates")
app.state.templates = templates

app.include_router(pages_routes.router)
app.include_router(rooms_routes.router)
app.include_router(questions_routes.router)
app.include_router(upvotes_routes.router)
app.include_router(events_routes.router)
app.include_router(export_routes.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    sm = get_sessionmaker()
    async with sm() as s:
        await s.execute(text("SELECT 1"))
    return {"status": "ok"}
