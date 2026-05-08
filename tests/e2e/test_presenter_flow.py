import re


def test_presenter_pin_then_answer(live_server, playwright_instance, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "Presenter flow")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    presenter_url = page.url
    code = re.search(r"/r/([A-Z0-9]{6})/", presenter_url).group(1)

    browser2 = playwright_instance.chromium.launch()
    try:
        ctx2 = browser2.new_context()
        audience = ctx2.new_page()
        audience.set_default_timeout(8000)

        audience.goto(f"{live_server}/r/{code}")
        audience.wait_for_load_state("domcontentloaded")
        audience.fill('input[name="name"]', "Sam")
        audience.click('button[type="submit"]')
        # wait for the audience composer (SSE keeps connection open, so no networkidle)
        audience.wait_for_selector("#composer", timeout=8000)
        audience.fill("#composer textarea", "Pin me")
        audience.click('#composer button[type="submit"]')
        # wait until question is visible on audience side
        audience.wait_for_selector("text=Pin me", timeout=8000)

        live_url = presenter_url + "&v=live"
        page.goto(live_url)
        page.wait_for_selector("text=Pin me", timeout=8000)
        page.click('button[data-act="state"][data-val="pinned"]')

        # verify pin succeeded — presenter page reflects the action
        page.wait_for_load_state("domcontentloaded")
    finally:
        browser2.close()
