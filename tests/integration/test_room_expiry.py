from datetime import UTC, datetime, timedelta

from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import Room


async def test_expired_room_is_swept(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]

    sm = get_sessionmaker()
    async with sm() as s:
        room = (await s.execute(select(Room).where(Room.code == code))).scalar_one()
        room.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    # Manually invoke the sweep logic instead of waiting 10 minutes
    async with sm() as s:
        await s.execute(sql_delete(Room).where(Room.expires_at < datetime.now(UTC)))
        await s.commit()

    async with sm() as s:
        result = await s.execute(select(Room).where(Room.code == code))
        assert result.scalar_one_or_none() is None
