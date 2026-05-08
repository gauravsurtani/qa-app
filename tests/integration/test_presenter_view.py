async def test_presenter_share_screen_first_load(client):
    create = await client.post("/rooms", json={"title": "Test"})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    r = await client.get(f"/r/{code}/host?t={token}")
    assert r.status_code == 200
    assert "Share with your audience" in r.text
    assert code in r.text


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
