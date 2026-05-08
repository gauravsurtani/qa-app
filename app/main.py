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
