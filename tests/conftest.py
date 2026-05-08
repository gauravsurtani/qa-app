from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("EMAIL_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        import app.routes.questions as _q

        _q._question_limiter = None
    except ImportError:
        pass
    try:
        import app.routes.upvotes as _u

        _u._upvote_limiter = None
    except ImportError:
        pass


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
