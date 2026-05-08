"""
SSE integration test.

httpx's ASGITransport buffers the entire response body before returning
any bytes to the caller. This makes it incompatible with infinite SSE
streams. Instead, we call the ASGI app directly and collect events via
an asyncio.Queue that is filled by the ASGI `send` callback.
"""
import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient


async def _collect_sse_events(
    app,
    path: str,
    num_events: int,
    timeout: float = 5.0,
) -> list[dict]:
    """
    Call the ASGI app directly for a streaming GET.
    Returns the first `num_events` SSE events as {"type": ..., "data": ...} dicts.
    """
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "headers": [],
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "server": ("test", 80),
        "client": ("127.0.0.1", 9999),
        "root_path": "",
    }

    event_queue: asyncio.Queue[dict] = asyncio.Queue()
    disconnect_event = asyncio.Event()
    buf = b""
    current_type: str | None = None

    async def receive():
        # After the response starts, signal disconnect once we have enough
        await disconnect_event.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal buf, current_type
        if message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            buf += chunk
            # Parse complete SSE frames from buffer
            while b"\n\n" in buf:
                frame, buf = buf.split(b"\n\n", 1)
                ev_type = None
                ev_data = None
                for raw_line in frame.split(b"\n"):
                    line = raw_line.decode()
                    if line.startswith("event:"):
                        ev_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        ev_data = json.loads(line.split(":", 1)[1].strip())
                if ev_type is not None and ev_data is not None:
                    await event_queue.put({"type": ev_type, "data": ev_data})

    # Run the ASGI app in a background task so the event loop stays free
    app_task = asyncio.create_task(app(scope, receive, send))

    collected: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while len(collected) < num_events:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            ev = await asyncio.wait_for(event_queue.get(), timeout=remaining)
            collected.append(ev)
        except asyncio.TimeoutError:
            break

    disconnect_event.set()
    app_task.cancel()
    try:
        await app_task
    except (asyncio.CancelledError, Exception):
        pass

    return collected


@pytest.mark.timeout(10)
async def test_sse_receives_question_created(client):
    # Reset rate limiter to avoid interference from earlier tests in the same run
    from app.routes.questions import get_question_limiter
    get_question_limiter().reset()

    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})

    from app.main import app as fastapi_app

    async def poster():
        await asyncio.sleep(0.2)
        await client.post(f"/r/{code}/questions", json={"text": "hello"})

    poster_task = asyncio.create_task(poster())
    events = await _collect_sse_events(fastapi_app, f"/r/{code}/events", num_events=2)
    await poster_task

    assert any(e["type"] == "connected" for e in events), f"no connected event in {events}"
    assert any(e["type"] == "question.created" for e in events), f"no question.created in {events}"
