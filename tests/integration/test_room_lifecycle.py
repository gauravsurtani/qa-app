async def test_create_room_returns_urls(client):
    resp = await client.post("/rooms", json={"title": "AI Talks"})
    assert resp.status_code == 201
    body = resp.json()
    assert "code" in body
    assert len(body["code"]) == 6
    assert body["audience_url"].endswith(f"/r/{body['code']}")
    assert "host?t=" in body["presenter_url"]


async def test_create_room_with_email(client):
    resp = await client.post(
        "/rooms",
        json={"title": "AI Talks", "presenter_email": "a@b.co"},
    )
    assert resp.status_code == 201


async def test_create_room_rejects_bad_email(client):
    resp = await client.post(
        "/rooms",
        json={"presenter_email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_end_session_requires_token(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    resp = await client.post(f"/r/{code}/end", follow_redirects=False)
    assert resp.status_code == 303


async def test_end_session_with_correct_token(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]

    resp = await client.post(f"/r/{code}/end?t={token}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    resp2 = await client.post(f"/r/{code}/end?t={token}")
    assert resp2.status_code == 409
