async def test_home_renders(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "Live Q&amp;A for your talk" in body
    assert "Made with" in body
    assert "DeepLearning.AI" in body
