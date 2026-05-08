# DLAI Q&A

Live Q&A web app. Audience scans QR, types name, asks + upvotes questions.
Presenter pins / answers / hides / stars in real time.

## Run locally

    uv sync --all-groups
    cp .env.example .env  # set SESSION_SECRET (32+ chars) and EMAIL_API_KEY (Resend)
    uv run uvicorn app.main:app --reload

## Test

    uv run pytest

## Deploy (Railway)

1. Create a new service, point to this repo.
2. Set env vars: `SESSION_SECRET`, `EMAIL_API_KEY`, `EMAIL_FROM_ADDRESS`, `APP_BASE_URL`.
3. Mount a volume at `/data`.
4. Set `SQLITE_PATH=/data/qa.db`.
