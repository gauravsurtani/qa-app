import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def _set_session_secret(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)


async def test_healthz_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
