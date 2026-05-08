async def _create_room_and_join(client, name="Sam"):
    r = await client.post("/rooms", json={})
    body = r.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    j = await client.post(f"/r/{code}/join", json={"name": name})
    assert j.status_code == 204
    return code, token


async def test_audience_can_ask_question(client):
    code, _ = await _create_room_and_join(client)
    r = await client.post(f"/r/{code}/questions", json={"text": "hello?"})
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "hello?"
    assert body["state"] == "live"
    assert body["upvote_count"] == 0
    assert body["author_name"] == "Sam"


async def test_question_requires_join_first(client):
    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    resp = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    assert resp.status_code == 403


async def test_question_too_long_rejected(client):
    code, _ = await _create_room_and_join(client)
    r = await client.post(f"/r/{code}/questions", json={"text": "x" * 281})
    assert r.status_code == 422


async def test_presenter_can_pin(client):
    code, token = await _create_room_and_join(client)
    create = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    qid = create.json()["id"]
    r = await client.patch(f"/r/{code}/questions/{qid}?t={token}", json={"state": "pinned"})
    assert r.status_code == 200
    assert r.json()["state"] == "pinned"


async def test_pin_replaces_previous_pin(client):
    code, token = await _create_room_and_join(client)
    q1 = (await client.post(f"/r/{code}/questions", json={"text": "1"})).json()["id"]
    q2 = (await client.post(f"/r/{code}/questions", json={"text": "2"})).json()["id"]
    await client.patch(f"/r/{code}/questions/{q1}?t={token}", json={"state": "pinned"})
    await client.patch(f"/r/{code}/questions/{q2}?t={token}", json={"state": "pinned"})

    r1 = await client.patch(f"/r/{code}/questions/{q1}?t={token}", json={"starred": True})
    assert r1.json()["state"] == "live"


async def test_rate_limit(client):
    from app.routes.questions import get_question_limiter

    get_question_limiter().reset()
    code, _ = await _create_room_and_join(client)
    for i in range(5):
        r = await client.post(f"/r/{code}/questions", json={"text": f"q{i}"})
        assert r.status_code == 201
    r = await client.post(f"/r/{code}/questions", json={"text": "one too many"})
    assert r.status_code == 429
