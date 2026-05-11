# AskUp ▲

> **Live Q&A that rises to the top.**
> Audience scans a QR code, asks questions, upvotes the ones they want answered. Presenter pins, marks done, hides, or stars in real time.

🚀 **Live:** [**askup.site**](https://askup.site) → tell your audience: _"askup.site — code `XYZ123`"_
📦 **Repo:** [github.com/gauravsurtani/qa-app](https://github.com/gauravsurtani/qa-app)
🧠 **How it was built:** [`docs/superpowers/specs/`](docs/superpowers/specs/2026-05-07-qa-app-design.md) → [`docs/superpowers/plans/`](docs/superpowers/plans/2026-05-08-qa-app-implementation.md) → 52+ atomic commits → live

---

## What it does

A Slido-style Q&A tool, but free, instant, brandable, and built end-to-end with zero accounts.

| You're the **presenter** | Your **audience** |
|-|-|
| Click "Start a session" — get a QR + 6-char room code | Scan the QR (or type the code at askup.site) |
| Project the QR on your screen, or paste the link in Slack | Type a name once, then ask questions |
| See questions arrive in real time on your dashboard | See everyone else's questions and **upvote** the good ones |
| **Pin** what you're answering now → audience sees "Answering Now" | Watch the room's currently-answering question light up |
| **Done** marks it answered (greyed out, sunk to the bottom of the queue) | See the upvote count flip and cards smoothly re-rank |
| **Hide** removes spam without telling anyone | |
| **Star** to come back to it later | |
| **Download CSV** of every question anytime | |
| **End session** → audience sees a graceful "Q&A has ended" page | |

---

## Why this exists

I needed a Q&A tool for talks where:
1. The audience could join with **zero friction** (no signup, no app install).
2. The presenter could **see everyone's questions in real-time** and pick which to answer.
3. Upvotes surface what the room actually cares about — not just the loudest voice.
4. Everything is **instant** (sub-300ms feel) and **looks like a paid SaaS product**.

Existing tools (Slido, Mentimeter) work but are paywalled and feel corporate. AskUp is opinionated about being free, fast, and minimal.

---

## Architecture (one paragraph)

A single **FastAPI** service, server-rendered **Jinja2 + HTMX** with ~300 lines of vanilla JS — no React, no build step. Real-time via **Server-Sent Events** fan-out from an in-process `asyncio.Queue` (one process, one worker, ≤50-person audience scope). Persistent **SQLite** on a Railway volume. **Motion One** + CSS keyframes for animations. **Deterministic gradient avatars** from name hash. **Cache-Control: no-cache** middleware on `/static/*` so deploys flush browser caches instantly.

```
                              ┌────────────────────────────┐
                              │  FastAPI (1 process)       │
                              │  ─────────────────────     │
                              │  • Jinja2 templates        │
                              │  • REST mutations          │
                              │  • SSE fan-out (asyncio.Q) │
                              │  • SQLite on /data volume  │
                              └────────────┬───────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       │                                       │
               Audience (mobile)                       Presenter (desktop)
               /XYZ123                                 /r/XYZ123/host?t=…
               scan → name → ask + upvote              pin / done / hide / star
```

---

## Tech stack

| Layer | Choice | Why |
|-|-|-|
| Backend | **FastAPI 0.115+ / Python 3.12** | Async-native, type-safe, one-language stack |
| DB | **SQLite + aiosqlite** | One file, zero ops, persists on Railway volume |
| Templates | **Jinja2 + HTMX** | Server-rendered = fast first paint, no build step |
| Realtime | **Server-Sent Events** | One-way fan-out is all we need; simpler than WebSockets |
| Frontend JS | **Vanilla + Motion One** | ~300 LOC total; no React, no bundler |
| Animations | **CSS keyframes + Motion One + Web Animations API** | Spring easing, FLIP for layout, prefers-reduced-motion respected |
| Fonts | **DM Sans + DM Mono** | Clean, modern, free |
| QR | **`qrcode` Python lib** | Brand-styled SVG |
| Tests | **pytest + httpx + Playwright** | 75 tests, ~80% coverage |
| Tooling | **uv, ruff, mypy** | Fast install, strict lint + types |
| Deploy | **Railway (Dockerfile)** | Single-service, persistent volume, generated SSL domain |
| Domain | **Hostinger DNS → askup.site** | ALIAS apex pointed at Railway |

---

## How it was built

This whole project was built using a **brainstorm → spec → plan → execute** workflow, with every step documented:

| Stage | Doc | Outcome |
|-|-|-|
| **1. Brainstorm** | conversational Socratic Q&A | 4 clarifying-question rounds → locked the product shape (no-login, ask + upvote, public default with presenter controls) |
| **2. Spec** | [`docs/superpowers/specs/2026-05-07-qa-app-design.md`](docs/superpowers/specs/2026-05-07-qa-app-design.md) | 15-section design doc covering architecture, data model, flows, brand, motion, error handling, deployment |
| **3. Plan** | [`docs/superpowers/plans/2026-05-08-qa-app-implementation.md`](docs/superpowers/plans/2026-05-08-qa-app-implementation.md) | 28-task TDD plan with full code for every step |
| **4. Execute** | git log | 52+ atomic commits, each shipping one task with passing tests |
| **5. Polish** | iterative design passes | Motion One animations, custom modals, FLIP transitions, premium typography, gradient avatars |
| **6. Deploy** | Railway + Hostinger | Custom domain, ALIAS apex DNS, auto-deploy on git push |

The spec and plan are committed — read them to see exactly how a Q&A app gets reasoned about from scratch.

---

## Run locally

```bash
git clone https://github.com/gauravsurtani/qa-app.git
cd qa-app
uv sync --all-groups
cp .env.example .env
# edit .env: set SESSION_SECRET to a 32+ char random string
#   e.g. SESSION_SECRET=$(openssl rand -hex 32)

uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 and click "Start a session." Done.

> **Requires:** Python 3.12+, [uv](https://github.com/astral-sh/uv).

---

## Test

```bash
# Unit + integration (~75 tests, ~2 seconds)
uv run pytest tests/unit tests/integration

# End-to-end with Playwright (chromium browser required)
uv run playwright install chromium
uv run pytest tests/e2e
```

> Combined `pytest` triggers a known pytest-asyncio + pytest-playwright event-loop conflict. Run them separately.

---

## Deploy (Railway)

1. **Push to GitHub** and create a new Railway service pointed at the repo.
2. **Add a volume** mounted at `/data`.
3. **Set env vars:**

```bash
SESSION_SECRET=<32+ random chars — openssl rand -hex 32>
SQLITE_PATH=/data/qa.db
LOG_LEVEL=INFO
APP_BASE_URL=https://${{RAILWAY_PUBLIC_DOMAIN}}    # or your custom domain
```

4. **Generate a domain** in Settings → Networking. Railway auto-issues an SSL cert.
5. **Optional: custom domain** — register on Hostinger/Namecheap, point an ALIAS at `<service>.up.railway.app`, update `APP_BASE_URL`.

Auto-deploy fires on every push to `master`.

### Optional: email-on-close

The Resend integration is wired up but disabled. To enable, set `EMAIL_API_KEY` + `EMAIL_FROM_ADDRESS`, then re-add the email field to `templates/home.html`. Without it, presenters use the **Download CSV** button in the header (works any time during or after a session).

---

## Project structure

```
qa-app/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, /healthz, static cache middleware
│   ├── config.py               # pydantic-settings env config
│   ├── db.py                   # async SQLAlchemy engine + sessions
│   ├── models.py               # Room, Participant, Question, Upvote
│   ├── schemas.py              # Pydantic DTOs
│   ├── auth.py                 # presenter token + audience cookie
│   ├── routes/                 # pages, rooms, questions, upvotes, events (SSE), export
│   ├── services/               # rooms, questions, pubsub, ratelimit, csv_export, email
│   └── utils/                  # code generator, ids, qr svg
├── templates/                  # Jinja2 (home, audience, presenter, fullscreen_qr, …)
├── static/
│   ├── css/                    # tokens, base, animations
│   └── js/                     # sse, upvote, modal, toast, avatar, shortcuts
├── tests/
│   ├── unit/                   # 35+ tests, pure logic
│   ├── integration/            # 40+ tests, full HTTP roundtrips + SSE
│   └── e2e/                    # 3 Playwright critical-path tests
├── docs/superpowers/
│   ├── specs/2026-05-07-*.md   # design spec
│   └── plans/2026-05-08-*.md   # implementation plan
├── Dockerfile
├── railway.toml
└── pyproject.toml
```

---

## What's intentionally simple

These are deliberately deferred to keep v1 tight:

- ❌ Multi-presenter / co-host (single token, anyone with the URL is the host)
- ❌ Question editing or deletion by author
- ❌ Threaded replies / comments
- ❌ Emoji reactions
- ❌ Persistent presenter accounts
- ❌ Spam / profanity / CAPTCHA filters
- ❌ Analytics dashboard
- ❌ Mobile native apps
- ❌ Internationalization

Easy to add later — the architecture leaves room for each.

---

## Credits

Made with ♥ by [**Gaurav Surtani**](https://www.linkedin.com/in/gaurav-surtani/).
Coral and slate palette borrowed from the DeepLearning.AI brand system.
Brainstormed, specced, planned, and built with Claude as a pair-programming partner.

If you use this, ship a star or send a screenshot — I'd love to see it in the wild.
