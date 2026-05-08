from unittest.mock import AsyncMock, patch


async def test_email_not_sent_without_address(client):
    with patch("app.routes.rooms.send_session_ended_email", new=AsyncMock()) as mock_send:
        create = await client.post("/rooms", json={})
        body = create.json()
        code = body["code"]
        token = body["presenter_url"].split("t=")[1]
        await client.post(f"/r/{code}/end?t={token}")
        mock_send.assert_not_awaited()


async def test_email_sent_when_address_provided(client):
    with patch("app.routes.rooms.send_session_ended_email", new=AsyncMock(return_value=True)) as mock_send:
        create = await client.post("/rooms", json={"presenter_email": "a@b.co", "title": "T"})
        body = create.json()
        code = body["code"]
        token = body["presenter_url"].split("t=")[1]
        await client.post(f"/r/{code}/join", json={"name": "Sam"})
        await client.post(f"/r/{code}/questions", json={"text": "hi"})

        r = await client.post(f"/r/{code}/end?t={token}")
        assert r.status_code == 200
        # BackgroundTasks may run after response; httpx test client awaits them.
        mock_send.assert_awaited_once()
        kwargs = mock_send.await_args.kwargs
        assert kwargs["to_address"] == "a@b.co"
        assert b"hi" in kwargs["csv_attachment"]
