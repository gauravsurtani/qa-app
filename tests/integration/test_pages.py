async def test_home_renders(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Ask" in body and "Up" in body  # AskUp wordmark
    assert "Live Q&amp;A that rises to the top" in body
    assert "Made with" in body
    assert "Gaurav" in body
