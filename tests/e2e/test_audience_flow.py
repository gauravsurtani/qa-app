import re


def test_audience_join_ask_upvote(live_server, page):
    page.goto(live_server + "/")
    page.fill('input[name="title"]', "Audience flow")
    page.click('button[type="submit"]')
    page.wait_for_url("**/r/*/host*")
    code = re.search(r"/r/([A-Z0-9]{6})/", page.url).group(1)

    page.goto(f"{live_server}/r/{code}")
    page.wait_for_load_state("domcontentloaded")
    page.fill('input[name="name"]', "Sam")
    page.click('button[type="submit"]')
    # join does window.location.reload() — wait for the audience composer to appear
    page.wait_for_selector("#composer", timeout=8000)

    page.fill("#composer textarea", "What about cost?")
    page.click('#composer button[type="submit"]')
    # Question appears via SSE; wait for it to render
    page.wait_for_selector("text=What about cost?", timeout=8000)

    page.click('[data-action="upvote"]')
    page.wait_for_function(
        'document.querySelector(".upvote-count") && document.querySelector(".upvote-count").textContent === "1"',
        timeout=8000,
    )
