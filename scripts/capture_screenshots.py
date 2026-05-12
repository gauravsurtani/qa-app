"""Capture README screenshots from the live site via Playwright.

Run from the repo root:

    uv run python scripts/capture_screenshots.py

Captures five PNGs into docs/img/:
  - home.png            -- homepage hero
  - share.png           -- presenter share screen (QR + room code)
  - audience.png        -- audience joined view with a pinned card + queue
  - presenter.png       -- presenter dashboard with the same room
  - fullscreen_qr.png   -- projector mode

Each capture uses 1440x900 (laptop-typical) for desktop views and 390x800
for the audience (iPhone-Pro-ish) view. Demo data is created via the
live API so the screenshots have realistic question content.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = "https://askup.site"
OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

QUESTIONS = [
    ("Priya",   "How do you scale this beyond 50 attendees?"),
    ("Sam",     "What was the hardest part of the build?"),
    ("Mansi",   "Will you open-source the deployment config?"),
    ("Alex",    "How does the realtime layer work with multiple workers?"),
    ("Jordan",  "Plans for threads/replies on questions?"),
]


def create_demo_room() -> tuple[str, str]:
    """Spin up a fresh demo room with realistic questions + upvotes + a pin."""
    with httpx.Client(base_url=BASE, timeout=20.0) as c:
        # Create room
        r = c.post("/rooms", json={"title": "AskUp — Live Demo"}).raise_for_status()
        body = r.json()
        code, token = body["code"], body["presenter_url"].split("t=")[1]

        # Seed several audience participants and questions
        question_ids: list[int] = []
        for i, (name, text) in enumerate(QUESTIONS):
            jar = httpx.Client(base_url=BASE, timeout=20.0)
            jar.post(f"/r/{code}/join", json={"name": name}).raise_for_status()
            q = jar.post(f"/r/{code}/questions", json={"text": text}).raise_for_status()
            qid = q.json()["id"]
            question_ids.append(qid)
            # Top 3 questions get a few upvotes from other "participants"
            if i < 3:
                for upvoter in QUESTIONS:
                    if upvoter[0] == name:
                        continue
                    voter = httpx.Client(base_url=BASE, timeout=20.0)
                    voter.post(f"/r/{code}/join", json={"name": upvoter[0]}).raise_for_status()
                    voter.post(f"/r/{code}/questions/{qid}/upvote").raise_for_status()
                    voter.close()
            jar.close()

        # Pin the top-voted question
        c.patch(
            f"/r/{code}/questions/{question_ids[0]}?t={token}",
            json={"state": "pinned"},
        ).raise_for_status()

    print(f"created demo room: code={code}")
    return code, token


def create_empty_room() -> tuple[str, str]:
    """Empty room — used to capture the share screen which only renders
    when there are zero questions in the queue."""
    with httpx.Client(base_url=BASE, timeout=20.0) as c:
        r = c.post("/rooms", json={"title": "AskUp"}).raise_for_status()
        body = r.json()
        return body["code"], body["presenter_url"].split("t=")[1]


def capture():
    # Empty room first (for share screen)
    empty_code, empty_token = create_empty_room()
    # Seeded room for presenter / audience / fullscreen captures
    code, token = create_demo_room()

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- Desktop captures (1440x900) ----
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = ctx.new_page()

        # Homepage
        page.goto(f"{BASE}/")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "home.png"), full_page=False)
        print("  ✓ home.png")

        # Presenter share screen (empty room — shows QR + room code hero)
        page.goto(f"{BASE}/r/{empty_code}/host?t={empty_token}")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "share.png"), full_page=False)
        print("  ✓ share.png")

        # Presenter dashboard (live view with questions + pinned)
        page.goto(f"{BASE}/r/{code}/host?t={token}&v=live")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "presenter.png"), full_page=False)
        print("  ✓ presenter.png")

        # Fullscreen QR
        page.goto(f"{BASE}/r/{code}/host/qr?t={token}")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "fullscreen_qr.png"), full_page=False)
        print("  ✓ fullscreen_qr.png")

        ctx.close()

        # --- Mobile capture (audience) ----
        m_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
        )
        m_page = m_ctx.new_page()
        # Join via API first so the page renders the participant view, not the
        # name form.
        api = httpx.Client(base_url=BASE, timeout=20.0)
        api.post(f"/r/{code}/join", json={"name": "You"}).raise_for_status()
        # Push the same cookie into the browser context
        for cookie in api.cookies.jar:
            m_ctx.add_cookies([{
                "name": cookie.name,
                "value": cookie.value,
                "domain": "askup.site",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }])
        api.close()

        m_page.goto(f"{BASE}/{code}")
        m_page.wait_for_load_state("domcontentloaded")
        m_page.wait_for_timeout(800)
        m_page.wait_for_timeout(1200)
        m_page.screenshot(path=str(OUT / "audience.png"), full_page=False)
        print("  ✓ audience.png")

        m_ctx.close()
        browser.close()

    print(f"\nAll screenshots saved to {OUT}/")


if __name__ == "__main__":
    capture()
