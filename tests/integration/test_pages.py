async def test_home_renders(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Ask" in body and "Up" in body  # AskUp wordmark
    assert "Live Q&amp;A that rises to the top" in body
    assert "Made with" in body
    assert "Gaurav" in body
    # Join-with-code form is on the homepage
    assert 'id="join-code-form"' in body
    assert 'name="code"' in body


async def test_short_url_renders_audience_view(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/{code}")
    assert r.status_code == 200
    assert "Join this Q&amp;A" in r.text  # name-entry form on first visit


async def test_invalid_short_url_returns_404(client):
    r = await client.get("/HELLO1")  # H not in alphabet, 6 chars but invalid
    assert r.status_code == 404


async def test_static_path_does_not_collide_with_short_url(client):
    # /healthz is shorter than 6 chars and registered before pages router; should still work
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
