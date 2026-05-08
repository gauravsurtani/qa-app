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
