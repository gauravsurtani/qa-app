async def _setup(client):
    r = await client.post("/rooms", json={})
    code = r.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    q = await client.post(f"/r/{code}/questions", json={"text": "hi"})
    return code, q.json()["id"]


async def test_upvote_increments(client):
    code, qid = await _setup(client)
    r = await client.post(f"/r/{code}/questions/{qid}/upvote")
    assert r.status_code == 200
    body = r.json()
    assert body["upvoted"] is True
    assert body["upvotes"] == 1


async def test_upvote_toggle(client):
    code, qid = await _setup(client)
    await client.post(f"/r/{code}/questions/{qid}/upvote")
    r = await client.post(f"/r/{code}/questions/{qid}/upvote")
    assert r.json()["upvoted"] is False
    assert r.json()["upvotes"] == 0


async def test_upvote_404_for_unknown_question(client):
    code, _ = await _setup(client)
    r = await client.post(f"/r/{code}/questions/9999/upvote")
    assert r.status_code == 404
