# AskUp

**Live Q&A that rises to the top.**

Audience scans QR, types name, asks + upvotes questions.
Presenter pins / answers / hides / stars in real time.

## Run locally

    uv sync --all-groups
    cp .env.example .env  # set SESSION_SECRET (32+ chars)
    uv run uvicorn app.main:app --reload

## Test

Unit + integration:

    uv run pytest tests/unit tests/integration

End-to-end (Playwright Chromium, requires `uv run playwright install chromium` first):

    uv run pytest tests/e2e

Combined `pytest` is currently incompatible due to a known pytest-asyncio / pytest-playwright event-loop conflict. Run the two suites separately.

## Deploy (Railway)

1. Create a new service, point to this repo.
2. Set env vars: `SESSION_SECRET`, `APP_BASE_URL`, `SQLITE_PATH=/data/qa.db`.
3. Mount a volume at `/data`.

Email-on-close is disabled in v1 — presenters download a CSV from the dashboard
instead. The Resend integration is still wired up internally; set `EMAIL_API_KEY`
+ `EMAIL_FROM_ADDRESS` and re-add the email field to `templates/home.html` to
re-enable.
