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
