# AskUp ▲

> **Live Q&A that rises to the top.** Free, no signup, real-time.

**[Try it → askup.site](https://askup.site)**  ·  Tell your audience: _"askup.site — code XYZ123"_

---

## What it does

- Audience scans a QR (or types a 6-char code) → asks + upvotes questions.
- Presenter sees everything live → pins the one being answered, marks done, hides spam, stars to revisit.
- Upvotes surface what the room actually wants answered — not the loudest voice.
- CSV export anytime. Rooms expire 24h after last activity.

## Quick start

```bash
uv sync --all-groups
cp .env.example .env          # set SESSION_SECRET to 32+ random chars
uv run uvicorn app.main:app --reload
```

Open <http://localhost:8000> and click **Start a session**.

Requires Python 3.12 and [uv](https://github.com/astral-sh/uv).

## Deploy (Railway)

1. New service from this repo.
2. Add a volume mounted at `/data`.
3. Set env vars: `SESSION_SECRET` (32+ chars), `SQLITE_PATH=/data/qa.db`, `APP_BASE_URL`.
4. Push to deploy.

## Test

```bash
uv run pytest tests/unit tests/integration   # 75 tests, ~2s
```

E2E (optional):

```bash
uv run playwright install chromium
uv run pytest tests/e2e
```

## Credits

Made by **[Gaurav Surtani](https://www.linkedin.com/in/gaurav-surtani/)** with ♥.
