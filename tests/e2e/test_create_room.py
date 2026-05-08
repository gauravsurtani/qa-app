def test_homepage_creates_room_and_redirects_to_share_screen(live_server, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "E2E Test")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    assert "Share with your audience" in page.content()
    assert page.locator("svg").count() >= 1  # QR is an SVG
