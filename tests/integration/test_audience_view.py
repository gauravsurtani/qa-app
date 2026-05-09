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


async def test_audience_get_sets_session_cookie(client):
    """Regression: previously the GET route relied on FastAPI's background-response
    merge to set the qa_session cookie, which silently dropped it for explicit
    TemplateResponse returns. Without this cookie, the join POST would set it but
    a subsequent reload could race and bounce the user back to the join form.
    """
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}")
    assert r.status_code == 200
    assert "qa_session" in r.cookies
    assert len(r.cookies["qa_session"]) >= 16


async def test_audience_get_short_url_sets_session_cookie(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/{code}")
    assert r.status_code == 200
    assert "qa_session" in r.cookies


async def test_join_short_url_alias_works(client):
    """Belt-and-suspenders: audience clients with cached old JS that POST to
    /{code}/join (instead of canonical /r/{code}/join) should still succeed.
    """
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.post(f"/{code}/join", json={"name": "Cached"})
    assert r.status_code == 204


async def test_short_url_join_form_targets_canonical_endpoint(client):
    """Regression: when audience hits the short URL /{code}, the rendered join
    form's JS must POST to /r/{code}/join (canonical), NOT to /{code}/join
    (which doesn't exist). Visiting via the short URL previously broke the
    join flow because the JS used window.location.pathname + '/join'.
    """
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/{code}")
    assert r.status_code == 200
    # Rendered HTML must reference the canonical /r/<CODE>/join path. The
    # current template builds it via `'/r/' + "<CODE>" + '/join'` so we look
    # for the JOIN_URL declaration plus the room code as separate fragments.
    assert "JOIN_URL" in r.text
    assert "'/r/'" in r.text
    assert f'"{code}"' in r.text
    # And it must NOT use the broken `window.location.pathname + '/join'` shape
    assert "window.location.pathname + '/join'" not in r.text


async def test_audience_get_does_not_overwrite_existing_cookie(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    # First visit lands cookie
    r1 = await client.get(f"/r/{code}")
    cookie = r1.cookies["qa_session"]
    # Second visit reuses it (no Set-Cookie)
    r2 = await client.get(f"/r/{code}")
    assert r2.status_code == 200
    # AsyncClient won't expose Set-Cookie if not present, so absence is the test
    assert "qa_session" not in r2.cookies or r2.cookies["qa_session"] == cookie
