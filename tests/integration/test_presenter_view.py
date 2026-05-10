async def test_presenter_share_screen_first_load(client):
    create = await client.post("/rooms", json={"title": "Test"})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    r = await client.get(f"/r/{code}/host?t={token}")
    assert r.status_code == 200
    # Share-screen anchors: eyebrow heading + the room code as hero
    assert "Share to join" in r.text
    assert code in r.text
    # Three primary actions are present
    assert "Project" in r.text
    assert "Copy link" in r.text
    assert "Open dashboard" in r.text
    # Bookmark warning is still there, just smaller
    assert "Bookmark this page" in r.text


async def test_presenter_wrong_token_redirects(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}/host?t=bogus", follow_redirects=False)
    assert r.status_code == 303


async def test_fullscreen_qr_route(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    r = await client.get(f"/r/{code}/host/qr?t={token}")
    assert r.status_code == 200
    assert "Scan to ask" in r.text


async def test_presenter_renders_pinned_question_in_slot(client):
    create = await client.post("/rooms", json={})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    await client.post(f"/r/{code}/join", json={"name": "A"})
    q = await client.post(f"/r/{code}/questions", json={"text": "pin me"})
    qid = q.json()["id"]
    await client.patch(f"/r/{code}/questions/{qid}?t={token}", json={"state": "pinned"})

    r = await client.get(f"/r/{code}/host?t={token}&v=live")
    assert r.status_code == 200
    # Pinned card rendered inside pinned-slot-active, not just in the queue
    assert "pinned-slot-active" in r.text
    assert "pin me" in r.text
    # Must carry the q-card-pinned class
    assert "q-card-pinned" in r.text
