async def test_audience_sees_join_form_first(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}")
    assert r.status_code == 200
    assert "Join this Q&amp;A" in r.text
    assert "Your name" in r.text


async def test_audience_sees_questions_after_join(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    await client.post(f"/r/{code}/questions", json={"text": "first?"})
    r = await client.get(f"/r/{code}")
    assert "first?" in r.text
    assert "Sam" in r.text


async def test_closed_room_shows_ended_message(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    await client.post(f"/r/{code}/end?t={token}")
    r = await client.get(f"/r/{code}")
    assert "ended" in r.text.lower()
