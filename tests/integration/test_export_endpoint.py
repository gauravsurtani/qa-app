async def test_export_csv_returns_attachment(client):
    create = await client.post("/rooms", json={"title": "T"})
    body = create.json()
    code = body["code"]
    token = body["presenter_url"].split("t=")[1]
    await client.post(f"/r/{code}/join", json={"name": "Sam"})
    await client.post(f"/r/{code}/questions", json={"text": "hi"})

    r = await client.get(f"/r/{code}/export.csv?t={token}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert f"qa-{code}" in r.headers["content-disposition"]
    assert "Sam" in r.text and "hi" in r.text


async def test_export_requires_token(client):
    create = await client.post("/rooms", json={})
    code = create.json()["code"]
    r = await client.get(f"/r/{code}/export.csv", follow_redirects=False)
    assert r.status_code == 303
