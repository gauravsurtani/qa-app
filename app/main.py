from contextlib import asynccontextmanager
from fastapi import FastAPI

from app import models  # noqa: F401  (registers tables with Base.metadata)
from app.config import get_settings
from app.db import create_all, init_engine
from app.routes import rooms as rooms_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    init_engine()
    await create_all()
    yield


app = FastAPI(title="qa-app", lifespan=lifespan)
app.include_router(rooms_routes.router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
