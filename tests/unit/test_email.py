from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()


async def test_returns_true_on_2xx():
    from app.services.email import send_session_ended_email

    with patch("httpx.AsyncClient") as mock_client_cls:
        instance = mock_client_cls.return_value.__aenter__.return_value
        instance.post = AsyncMock()
        instance.post.return_value.status_code = 200
        instance.post.return_value.text = "ok"
        ok = await send_session_ended_email(
            to_address="a@b.co",
            subject="x",
            html_body="<p>hi</p>",
            csv_attachment=b"hi",
            csv_filename="x.csv",
        )
        assert ok is True


async def test_retries_on_5xx_then_fails():
    from app.services.email import send_session_ended_email

    with (
        patch("app.services.email.asyncio.sleep", new=AsyncMock()),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        instance = mock_client_cls.return_value.__aenter__.return_value
        instance.post = AsyncMock()
        instance.post.return_value.status_code = 503
        instance.post.return_value.text = "bad"
        ok = await send_session_ended_email(
            to_address="a@b.co",
            subject="x",
            html_body="<p>hi</p>",
            csv_attachment=b"hi",
            csv_filename="x.csv",
            max_retries=2,
        )
        assert ok is False
        assert instance.post.await_count == 2


async def test_skips_when_no_api_key(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.services.email import send_session_ended_email

    ok = await send_session_ended_email(
        to_address="a@b.co",
        subject="x",
        html_body="<p>hi</p>",
        csv_attachment=b"hi",
        csv_filename="x.csv",
    )
    assert ok is False
