import asyncio
import json
from typing import AsyncIterator

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
