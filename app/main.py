import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import delete

from app.config import get_settings
from app.db import create_all, dispose_engine, init_engine
from app import models  # noqa: F401  (registers tables with Base.metadata)
from app.routes import events as events_routes
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
    from app.db import get_sessionmaker
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
app.include_router(rooms_routes.router)
app.include_router(questions_routes.router)
app.include_router(upvotes_routes.router)
app.include_router(events_routes.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
