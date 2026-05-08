# Q&A App — Design Spec

**Date:** 2026-05-07
**Author:** Gaurav Surtani (with Claude)
**Status:** Approved (brainstorming complete, ready for implementation plan)

---

## 1. Overview

A live Q&A web app for presenters. Audience scans a QR code on the speaker's screen, types their name, and asks questions. Other audience members can upvote questions. The presenter sees all questions in real time and chooses which to answer, marking them as pinned, answered, hidden, or starred.

Think Slido — minimum-friction, no accounts, deploy-once. Branded as DeepLearning.AI.

**Post-session:** Presenter can download a CSV of all questions anytime (during or after the session) from the dashboard. Optionally, a presenter can enter an email at room creation and receive a CSV + permalink automatically when the session ends. Email is collected for that single purpose only — no marketing, no analytics, no third-party sharing.

**Out of scope for v1:** spam filtering, profanity filter, CAPTCHA, analytics dashboard, multi-presenter roles, threaded replies, emoji reactions, question editing by author, persistent presenter accounts, mobile/native apps.

---

## 2. Constraints & decisions

| Question | Decision |
|-|-|
| Audience identity | Type a name on join. No login. Cookie-tracked session. |
| Question features | Ask + upvote. No comments / threading. |
| Visibility model | Public by default. Presenter can pin / answer / hide / star. Hidden questions disappear from audience but remain in presenter "Hidden" tab. |
| Presenter identity | No login. "Start session" creates a room and gives a secret presenter URL with a 32-byte token. Bookmark = the only way back. |
| Scale | ≤50 audience per room. Single Railway service, single worker. |
| Tech stack | FastAPI + Jinja2 + HTMX + SQLite + Server-Sent Events. One service. |
| Deployment | Railway, Dockerfile-based, persistent volume for SQLite. |
| Branding | DeepLearning.AI — coral primary (`#F65B66`), Inter font, slate neutrals. |
| Post-session data | CSV export (always available via dashboard button); optional email-on-close (presenter opts in by entering email at room creation). Email never used for anything other than sending Q&A archive. |

---

## 3. System architecture

```
                        ┌─────────────────────────┐
                        │  Single FastAPI service │
                        │  (Railway, 1 dyno)      │
                        ├─────────────────────────┤
                        │  • Routes (HTML pages)  │
                        │  • REST API (mutations) │
                        │  • SSE stream (push)    │
                        │  • SQLite (volume)      │
                        └────────┬────────────────┘
                                 │
                ┌────────────────┴───────────────────┐
                │                                    │
        Audience view (mobile)              Presenter view (desktop)
        /r/{roomCode}                       /r/{roomCode}/host?t={token}
```

**Three responsibilities, one process:**

| Responsibility | Implementation |
|-|-|
| Serve HTML pages | FastAPI + Jinja2 templates |
| Mutations (ask, vote, pin, hide, star, answer) | REST endpoints, called by HTMX `hx-post` |
| Real-time push to all viewers | Server-Sent Events (one-way fanout, no WebSocket complexity) |
| Persistence | SQLite on Railway-mounted volume |

**Two URLs per room:**
- Audience URL: `/r/{roomCode}` — what the QR encodes
- Presenter URL: `/r/{roomCode}/host?t={presenterToken}` — secret, acts as auth

The presenter token is a 32-byte URL-safe random string. Possession of the URL = presenter rights. No second factor.

---

## 4. Data model

Four tables. SQLite, normalized except for one denormalized counter for sort speed.

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│ rooms                   │1       *│ questions                    │
├─────────────────────────┤─────────┤──────────────────────────────┤
│ id           (pk)       │         │ id              (pk)         │
│ code         (unique)   │         │ room_id         (fk)         │
│ presenter_token         │         │ participant_id  (fk)         │
│ title                   │         │ author_name     (snapshot)   │
│ presenter_email (null)  │         │ text                         │
│ created_at              │         │ state    (live|pinned|       │
│ last_activity_at        │         │           answered|hidden)   │
│ expires_at              │         │ starred         (bool)       │
│ status                  │         │ upvote_count    (denorm)     │
│ closed_at  (nullable)   │         │ created_at                   │
│ email_sent_at (nullable)│         └──────────┬───────────────────┘
└───────┬─────────────────┘                    │1
        │1                                     │ *
        │ *                                    │
┌───────▼─────────────────┐           ┌────────▼─────────────┐
│ participants            │           │ upvotes              │
├─────────────────────────┤           ├──────────────────────┤
│ id              (pk)    │           │ question_id    (fk)  │
│ room_id         (fk)    │1        * │ participant_id (fk)  │
│ session_id  (cookie)    ├───────────│ created_at           │
│ name                    │           │ PK(question_id,      │
│ joined_at               │           │    participant_id)   │
└─────────────────────────┘           └──────────────────────┘
```

**Field details and rationale:**

| Field / decision | Notes |
|-|-|
| `rooms.code` | 6 chars, URL-safe alphabet (no ambiguous 0/O, 1/l/I), e.g. `K7M9PQ`. Easy to share verbally. |
| `rooms.presenter_token` | 32-byte URL-safe random (`secrets.token_urlsafe(32)`). |
| `rooms.status` | `active` / `closed` (set when presenter ends session). Closed rooms reject new questions/upvotes but stay readable until `expires_at`. |
| `rooms.expires_at` | Computed as `last_activity_at + 24h`. Cron sweep (every 10 min) hard-deletes rows past this and cascades to questions/upvotes/participants. When status flips to `closed`, `last_activity_at` is frozen — so a closed room is auto-deleted exactly 24h after closure. An idle (never-closed) active room is also deleted 24h after last write. |
| `rooms.presenter_email` | Optional. Validated on entry (RFC 5322-lite). Used **only** to send the post-session email. Never logged in plaintext, never used for marketing, never shared. Stored alongside the room and deleted when the room is deleted (24h after close). |
| `rooms.closed_at` | Timestamp set when presenter ends the session. Drives the email-send job and used as the user-facing "session ended at" display. |
| `rooms.email_sent_at` | Timestamp of successful CSV email delivery. Null until sent. Used to ensure the email is sent at most once per room (idempotent retry on transient failure). |
| `participants.session_id` | HTTP-only cookie value. Persists name and upvote dedup across page refreshes. Per-room scope. |
| `questions.author_name` | Snapshot at write time. If participant later renames, prior questions retain original attribution. |
| `questions.state` | Single enum, mutually exclusive (`live`, `pinned`, `answered`, `hidden`). Only one question per room can be `pinned`. |
| `questions.starred` | Boolean, orthogonal to `state`. Presenter bookmark for "revisit later." |
| `questions.upvote_count` | Denormalized for ORDER BY performance. Updated atomically with each upvote insert/delete. |

**Indexes:**
- `rooms.code` — unique
- `participants(room_id, session_id)` — unique
- `questions(room_id, state, upvote_count DESC, created_at DESC)` — primary list query
- `upvotes(question_id, participant_id)` — composite PK

---

## 5. User flows

### 5.1 Presenter (admin) journey

```
[1] HOMEPAGE — GET /
    Visitor sees "Live Q&A for your talk" hero with:
      • optional Title input
      • optional Email input ("send me a copy when the session ends")
        with helper microcopy: "We only use this to email your Q&A
         archive. No marketing, no sharing."
      • primary "Start a session →" button

[2] CREATE ROOM — POST /rooms { title?, presenter_email? }
    Server validates email format if present, generates code + token,
    inserts row, redirects to: /r/{code}/host?t={token}

[3] PRESENTER DASHBOARD (first load — share screen)
    Shows: QR code (image of audience URL), 6-char room code, copyable
    direct link, "Show fullscreen QR" button, and a "Bookmark this page —
    it's your only way back" callout.

[4] FULLSCREEN QR — projector mode
    Big QR + "qa.dlai.app · K7M9PQ" text, dark backdrop, ESC to exit.

[5] DASHBOARD DURING THE TALK — split-pane layout
    Left: ANSWERING NOW + stats. Right: Live queue with action buttons
    (Pin / Answer / Hide / Star). Updates via SSE as audience submits.
    Header has "Download CSV" button — works anytime (during or after).

[6] END SESSION — confirmation modal → status = closed
    Audience sees "This Q&A has ended. Thanks!" Read-only for 24h.
    If presenter provided an email, an async job sends:
      • subject: "Your Q&A session '<title>' has ended"
      • body: stats summary + link back to read-only room
      • attachment: questions.csv
    On success, email_sent_at is stamped. On failure, retried up to
    3 times with exponential backoff; surfaced as banner on the
    closed room view ("Email failed to send. Download CSV manually.").
```

### 5.4 CSV export

```
GET /r/{code}/export.csv  (presenter-only, requires valid token)

Response: text/csv; Content-Disposition: attachment;
          filename="qa-{code}-{YYYY-MM-DD}.csv"

Columns:
  question_id, author_name, text, state, starred,
  upvote_count, created_at, room_title, room_code
```

Available at any time — during a live session (snapshot of current state) or after close (final archive). One-line CSV per question. UTF-8 with BOM so Excel opens it correctly.

### 5.5 Email-on-close (server-side job)

```
trigger: POST /r/{code}/end (presenter ends session)
            ↓
        update rooms.status='closed', closed_at=now()
            ↓
        if rooms.presenter_email is not null and email_sent_at is null:
            enqueue email job (background task in same process)
            ↓
        email job:
            • render CSV from DB
            • render HTML email (Jinja template, brand-styled)
            • POST to email provider API (Resend default)
            • on 2xx: stamp email_sent_at = now()
            • on failure: log + retry (3 attempts, 2s/8s/32s backoff)
            • on final failure: leave email_sent_at null;
              presenter sees banner on closed-room view
```

The email itself is brand-styled to match the app — coral header, Inter font, footer "Made with ♥ from Gaurav & DeepLearning.AI", and a privacy line: *"We're emailing you because you asked us to. We won't use your address for anything else."*

### 5.2 Audience journey

```
[1] SCAN QR → GET /r/{code}
    First visit: "Enter your name" form (or check "Stay anonymous"
    only if room.allow_anon).
    POST /r/{code}/join {name} sets session cookie, redirects.
    Returning: cookie present → render audience view directly.

[2] AUDIENCE VIEW
    Header: room title.
    Pinned slot: "ANSWERING NOW" card (only when one is pinned).
    Tabs: [Live] [Answered].
    Sorted: upvote_count DESC, created_at DESC.
    Sticky bottom: composer (280-char textarea + Send).

[3] ASK → POST /r/{code}/questions {text}
    Optimistic: card appears at top of list immediately.
    Server confirms via SSE event question.created.

[4] UPVOTE → POST /r/{code}/questions/{id}/upvote
    Optimistic: count increments + arrow fills coral.
    Toggle: tap again removes vote.
    Server broadcasts question.upvoted to all clients.
```

### 5.3 Presenter actions

Each question card has 4 inline buttons:

| Action | Endpoint | Effect |
|-|-|-|
| 📌 Pin | `PATCH /r/{code}/questions/{id}` `{state: "pinned"}` | Card moves to "Answering Now" slot. Audience sees it pinned. Only one at a time — pinning a new one un-pins the previous. |
| ✓ Answered | `PATCH .../questions/{id}` `{state: "answered"}` | Card moves to "Answered" tab in both views. Greyed in main feed. |
| ⊘ Hide | `PATCH .../questions/{id}` `{state: "hidden"}` | Disappears from audience entirely. Stays in presenter "Hidden" tab — un-hide possible. |
| ⭐ Star | `PATCH .../questions/{id}` `{starred: bool}` | Toggle. Yellow indicator on card. Presenter has "Starred" tab to revisit. Orthogonal to state. |

**Default sort:** `upvote_count DESC, created_at DESC`. Toggle for "Newest first."

---

## 6. View layouts

### 6.1 Audience (mobile-first, ~360–400px)

```
┌────────────────────────────────┐
│ Room: AI Talks 2026     ⋮      │  coral header, room title
├────────────────────────────────┤
│ Asking as: Sam       [edit]    │
├────────────────────────────────┤
│ ┏━━ ANSWERING NOW ━━━━━━━━━━┓ │  pinned slot (only when pinned)
│ ┃ "How does RLHF differ      ┃ │
│ ┃  from DPO at scale?"       ┃ │
│ ┃ — Priya          ▲ 14      ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
├────────────────────────────────┤
│ [ Live ] [ Answered ]          │  tabs
├────────────────────────────────┤
│ ┌─ Question card ─────────┐    │
│ │ "What about cost..."    │    │
│ │ — Sam (you)      ▲ 8    │    │
│ └─────────────────────────┘    │
│ ┌─────────────────────────┐    │
│ │ "Will this work for..." │    │
│ │ — Anonymous     ▲ 3 ✓   │    │  ✓ = you upvoted
│ └─────────────────────────┘    │
│ … more cards, sorted by ▲      │
├────────────────────────────────┤
│ ┌─ Ask a question ─────────┐   │  sticky bottom composer
│ │ [text area]              │   │
│ │ 0/280            [Send]  │   │
│ └──────────────────────────┘   │
└────────────────────────────────┘
```

### 6.2 Presenter (desktop, ≥1200px)

```
┌──────────────────────────────────────────────────────────────────┐
│ Room: AI Talks 2026 | QR ⊞ | url 📋 | ● 23 listening | End ssn │
├──────────────────────────────┬───────────────────────────────────┤
│ ANSWERING NOW                │ Question queue                    │
│ ┌──────────────────────────┐ │ [Live][Starred][Answered][Hidden] │
│ │ "How does RLHF differ    │ │ Sort: [▲ Top] [⏱ New]            │
│ │  from DPO?"              │ │ ┌────────────────────────────────┐│
│ │ — Priya       ▲ 14       │ │ │"What about cost..."   ▲ 8     ││
│ └──────────────────────────┘ │ │ — Sam · 2m                     ││
│ [unpin]                      │ │ [📌 Pin][✓ Ans][⊘ Hide][⭐ Star] ││
│                              │ ├────────────────────────────────┤│
│ Stats                        │ │"Will this work for..."  ▲ 3   ││
│ • 23 participants            │ │ — Anonymous · 4m               ││
│ • 14 questions               │ │ [📌 Pin][✓ Ans][⊘ Hide][⭐ Star] ││
│ • 38 upvotes                 │ ├────────────────────────────────┤│
│                              │ │ … more                         ││
│ Settings                     │ │                                ││
│ • [ ] allow anon names       │ │                                ││
│ • [✓] allow upvoting         │ │                                ││
│ • [ ] freeze new questions   │ │                                ││
└──────────────────────────────┴───────────────────────────────────┘
```

### 6.3 Fullscreen QR (projector mode)

Big QR (~600px), audience URL + 6-char code in large type, dark backdrop. ESC to exit. Pinch-zoom locked (`viewport-fit=cover`).

### 6.4 UX rules

| Rule | Why |
|-|-|
| Audience composer is **sticky bottom** | One-handed thumb reach on phone |
| Pinned card always visible at top of both views | The whole point of pinning is "look at this now" |
| Presenter actions are inline buttons on each card | Live event = speed; no menus, no clicks-into-detail |
| Hidden questions invisible to audience | Moderation should not look like censorship |
| Presenter has Live / Starred / Answered / Hidden tabs | Hidden tab makes hide reversible |
| Both views update via SSE | Real-time, no refresh button anywhere |

---

## 7. Brand styling — DeepLearning.AI (coral primary)

**Typography:** `Inter` with system fallback (`ui-sans-serif, system-ui, sans-serif, Apple Color Emoji, Segoe UI Emoji`). Loaded from Google Fonts (single weight subset: 400/500/600/700).

**Color palette (extracted from compiled deeplearning.ai CSS):**

| Role | Hex | Use |
|-|-|-|
| **Primary coral** | `#F65B66` | Header, primary buttons, focus accents, upvote-active arrow |
| **Coral hover/deep** | `#EE414D` | Button hover/pressed |
| **Light coral bg** | `#FED7DA` | Pinned card subtle tint |
| **Coral pale tint** | `#FFF5F6` | Softest highlight backgrounds |
| **Teal accent** | `#237B94` | Secondary CTAs, "you" badge (rare) |
| **Light teal** | `#36A3C8` | Link hover, info chips |
| **Deep navy** | `#002566` | Heading text alternative |
| `#0F172A` | slate-900 | Primary text |
| `#334155` | slate-700 | Secondary text |
| `#64748B` | slate-500 | Muted text |
| `#94A3B8` | slate-400 | Placeholder, disabled |
| `#E2E8F0` | slate-200 | Card borders |
| `#F1F5F9` | slate-100 | Page background |
| `#F8FAFC` | slate-50 | Section backgrounds |

**CSS custom properties (`static/css/tokens.css`):**

```css
:root {
  /* DLAI primary */
  --dlai-coral:        #F65B66;
  --dlai-coral-deep:   #EE414D;
  --dlai-coral-bg:     #FED7DA;
  --dlai-coral-tint:   #FFF5F6;

  /* DLAI secondary */
  --dlai-teal:         #237B94;
  --dlai-teal-light:   #36A3C8;
  --dlai-navy:         #002566;

  /* Neutrals */
  --slate-900: #0F172A;
  --slate-700: #334155;
  --slate-500: #64748B;
  --slate-400: #94A3B8;
  --slate-200: #E2E8F0;
  --slate-100: #F1F5F9;
  --slate-50:  #F8FAFC;

  --radius-sm: 8px;
  --radius-md: 12px;

  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
```

**Component spec:**

| Element | Spec |
|-|-|
| Header bar | bg `#F65B66`, white text, height `56px` mobile / `64px` desktop, 1% grain texture overlay |
| Primary button | bg `#F65B66`, white text, radius `8px`, hover `#EE414D`, no shadow |
| Secondary button | bg white, border `1px solid #E2E8F0`, text `#0F172A`, hover bg `#F1F5F9` |
| Card | bg white, border `1px solid #E2E8F0`, radius `12px`, padding `16px` |
| Pinned card | bg `#FED7DA` at 30%, border `2px solid #F65B66`, subtle coral glow |
| Answered card | bg `#F1F5F9`, text muted to `#64748B` |
| Upvote button | inactive: `#64748B` outline arrow; active: `#F65B66` filled, count bold coral |
| Input | border `1px solid #E2E8F0`, focus ring `2px solid #F65B66`, radius `8px` |
| QR code | `#0F172A` foreground on white (coral fails contrast for QR readers) |
| "You" badge | small chip, bg `#237B94`, text white (teal as rare differentiator) |

**Mental model:** Coral = brand. Header, primary buttons, pinned highlight all wear coral. Teal is rare secondary (the "you" badge only). Slate carries everything else.

---

## 8. Polish, motion & premium layer

### 8.1 Motion principles

| Principle | Value |
|-|-|
| Duration | 180–320ms |
| Entrance easing | `cubic-bezier(0.32, 0.72, 0, 1)` (Apple) |
| Exit easing | `cubic-bezier(0.4, 0, 0.2, 1)` (Material) |
| Stagger | 40ms between siblings |
| `prefers-reduced-motion` | Collapse to opacity-only fades at 100ms |
| Layout transitions | FLIP technique (First, Last, Invert, Play) |

### 8.2 Animation catalog

| Event | Animation |
|-|-|
| New question arrives | slide-down 12px + fade + scale 0.96→1, 280ms; coral left-border pulse 1.5s as "new" flag |
| Upvote tapped | button scale 1.0→1.18→1.0, 220ms; arrow fills outline→coral; count digit slide-flip; **optimistic update before server reply** |
| Pin question | FLIP morph from queue to "Answering Now" slot, 320ms; previously pinned reverses |
| Mark answered | coral ripple from button; card fade to 50%, 240ms; slide to Answered tab; toast "Marked answered [Undo]" |
| Hide | card collapse height + fade, 240ms; toast "Hidden [Undo]" 5s |
| Star | star scale 0→1.2→1, 280ms spring; fills with coral |
| Tab switch | cross-fade with 8px Y-slide, 200ms |
| QR fullscreen open | QR scales from origin; backdrop fades to 95%, 280ms ease-out |
| Initial load | skeleton shimmer; cards stagger-fade 40ms apart |
| Reconnecting | banner slides down with pulsing coral dot; slides up on reconnect |
| 50th question | one-time confetti burst from header (1.2s) — delight moment |
| Button hover | bg crossfade coral→coral-deep, 120ms; subtle 1px Y lift |
| Input focus | ring 0→2px expand, 140ms; border darkens to coral |

### 8.3 Premium details

| Detail | Description |
|-|-|
| Optimistic upvotes | Count + arrow update instantly; rollback only if server rejects |
| Deterministic avatars | 32px gradient swatch from name hash (5–6 curated coral/teal/navy gradients) |
| Live audience pill | Header `● 23 listening` — coral dot pulses gently, updates via SSE |
| Custom QR styling | Rounded modules, 3 coral position-marker squares (Stripe-style), DLAI logomark in center |
| Sticky composer with smart focus | `/` keypress on desktop auto-focuses; mobile dismisses keyboard on send |
| Empty states | "Be the first to ask 👋" illustration; QR mode hint before first join |
| Rolling-digit count transitions | CSS `@property` for unitless number transitions |
| Coral header grain | 1% opacity noise overlay — keeps flat coral from looking generic |
| Toast system | Single bottom-center queue, auto-dismiss, max 2 stacked |
| Presenter keyboard shortcuts | `P` pin top, `A` answer, `H` hide, `S` star, `J/K` move selection, `?` shortcut sheet |
| Pinch-zoom-locked QR | `viewport-fit=cover` for projector use |

### 8.4 Tooling

| Layer | Tool |
|-|-|
| Animation engine | CSS transitions + Web Animations API; **Motion One** (3.8 KB) for FLIP |
| Confetti | `canvas-confetti` (4 KB) |
| Icons | Lucide (tree-shaken subset) |
| QR | `qrcode` (Python) → SVG, brand-styled in CSS |
| Skeleton | Pure CSS shimmer keyframes |

### 8.5 Footer (every page except fullscreen QR)

```
···························································
   Made with ♥ from Gaurav & DeepLearning.AI
   [GitHub] · [Privacy] · v0.1.0
···························································
```
- Text color: `slate-500`
- Heart: coral (`#F65B66`), 1.5s breathing pulse (1.0 → 1.08 → 1.0)
- Centered, 48px vertical padding
- Hidden in fullscreen QR mode

### 8.6 Accessibility guardrails

- All interactive elements ≥ 44px touch target
- Visible focus rings (`2px solid coral`); never `outline: none` without replacement
- Coral on white = 4.6:1 contrast ✓; white on coral = 4.6:1 ✓
- `aria-live="polite"` on question list (screen readers announce new questions)
- `prefers-reduced-motion` collapses all motion to 100ms opacity fades
- All animations ≤ 320ms (animation never becomes a blocker)

---

## 9. Real-time updates

### 9.1 SSE event types (`GET /r/{code}/events`)

```
question.created       { id, author_name, text, state, upvotes, created_at }
question.upvoted       { id, upvotes }
question.state_changed { id, state, starred }
question.deleted       { id }
room.settings_changed  { allow_anon, allow_upvote, frozen }
room.closed            { reason }
ping                   { ts }                      # every 20s, keepalive
```

### 9.2 Connection lifecycle

```
client connects
   │
   ├─► GET /r/{code}/state          # one-time snapshot
   │     (room + all questions + my_upvotes)
   │     │
   │     ▼  render initial DOM
   │
   └─► GET /r/{code}/events          # SSE long-lived
         │
         ▼  on each event → update DOM in place
         │
         ▼  on disconnect → exponential backoff (1s, 2s, 4s, max 30s)
            on reconnect → re-fetch /state to resync
```

### 9.3 Server-side fanout

```
In-memory: dict[room_id, set[asyncio.Queue]]

POST /r/.../questions   → DB insert
                        → publish event to all queues for that room
                        → each open SSE response drains its queue → flush
```

No Redis, no pub/sub. One Python process, single worker. If process restarts, clients reconnect and re-fetch state.

---

## 10. Error handling

| Scenario | Response |
|-|-|
| Empty / whitespace-only question | 422; inline "Question cannot be empty" |
| Question >280 chars | 413; live counter disables Send at limit |
| Duplicate upvote (same participant + question) | Composite PK rejects insert; return 200 idempotently with current count |
| Rate limiting per participant | 5 questions/min, 30 upvotes/min → 429; toast "slow down a sec" |
| Room expired (24h since last activity) | 410 Gone; full-screen "This room has ended" |
| Invalid presenter token | Silent redirect to audience view (no enumeration oracle) |
| Audience refresh mid-typing | Form state lost (acceptable); cookie persists name + upvotes |
| Presenter closes tab | Token URL bookmarkable; reopen and resume |
| Network drop mid-submit | HTMX retries POST once; then "couldn't send — try again" toast |
| SSE disconnect | Native EventSource auto-reconnect with backoff; banner during disconnect |
| Two presenters open simultaneously | Both see same state via SSE; last action wins |
| Hidden by mistake | "Hidden" tab allows un-hide |
| DB write fails | 500; generic toast "couldn't save — try again" |
| Invalid email format at room creation | 422; inline error "Please enter a valid email or leave blank" |
| Email provider API down / rate limited | Retry 3x with backoff; on final failure, log + show banner on closed-room view: "Couldn't email your archive. Download the CSV here." |
| Email job runs after room data is gone | Should not happen (email job runs synchronously after close, before 24h sweep). Defensive check: if room is missing when job runs, silently abort. |
| Presenter wants to remove their email | Not possible in v1 (no edit). Email is deleted with the room 24h after close. Documented in privacy notice. |

**Explicitly NOT in v1:**
- Spam / profanity filter
- CAPTCHA
- Question editing or deletion by author
- Multi-presenter roles
- Emoji reactions / threading

---

## 11. Project structure

```
qa-app/
├── app/
│   ├── main.py                  # FastAPI entry, lifespan, route mounting
│   ├── config.py                # Settings (pydantic-settings, env-driven)
│   ├── db.py                    # SQLite engine + session, schema bootstrap
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic DTOs
│   ├── routes/
│   │   ├── pages.py             # GET /, /r/{code}, /r/{code}/host
│   │   ├── rooms.py             # POST /rooms, room state, end session
│   │   ├── questions.py         # POST/PATCH/DELETE on questions
│   │   ├── upvotes.py           # POST/DELETE upvote
│   │   ├── events.py            # GET /r/{code}/events (SSE)
│   │   └── export.py            # GET /r/{code}/export.csv
│   ├── services/
│   │   ├── rooms.py             # business logic (create/expire/close)
│   │   ├── questions.py         # state transitions, validation
│   │   ├── pubsub.py            # in-memory room → queue fanout
│   │   ├── ratelimit.py         # token bucket per (room, participant)
│   │   ├── csv_export.py        # CSV streaming for /export.csv
│   │   └── email.py             # provider client (Resend), retry, idempotency
│   ├── auth.py                  # presenter token + audience cookie
│   └── utils/
│       ├── codes.py             # 6-char room code generator (no 0/O/1/l/I)
│       ├── qr.py                # QR SVG renderer with brand styling
│       └── ids.py               # ulid / nanoid helpers
├── templates/                   # Jinja2
│   ├── base.html                # shell + footer
│   ├── home.html                # landing
│   ├── audience.html
│   ├── presenter.html
│   └── partials/                # HTMX swap fragments
│       ├── question_card.html
│       └── pinned_card.html
├── static/
│   ├── css/
│   │   ├── tokens.css           # CSS custom properties
│   │   ├── base.css
│   │   └── animations.css
│   ├── js/
│   │   ├── sse.js               # EventSource + reconnect + dispatch
│   │   ├── upvote.js            # optimistic update
│   │   ├── shortcuts.js         # presenter keyboard shortcuts
│   │   └── motion.js            # tiny FLIP helpers
│   └── img/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── migrations/                  # alembic
├── Dockerfile
├── railway.toml
├── pyproject.toml
└── README.md
```

---

## 12. Testing strategy

**Coverage target: 80%+.** Three tiers, prioritized.

### Tier 1 — Unit (pytest + pytest-asyncio, target <3s)

- Question state transitions (`live → pinned → answered → hidden` and reverse paths). Verify only one `pinned` per room.
- Upvote idempotency: same participant + same question = no duplicate.
- Room expiry logic: expired rooms reject mutations with 410.
- Token verification: constant-time compare for presenter token.
- Rate limiter: 429 after thresholds, resets per window.
- Validators: question text 1..280 chars, name 1..40 chars, whitespace-only rejected.

### Tier 2 — Integration (httpx.AsyncClient + per-test SQLite, target <15s)

- Full lifecycle: create room → audience joins → asks → upvotes → presenter pins/answers/hides → end session.
- SSE: subscribe; trigger mutation in another client; assert event arrives within 500ms.
- Cookie-based participant identity: refresh persists name + upvotes.
- Presenter token paths: wrong token → silent redirect (no oracle).
- Concurrent upvotes: 50 simultaneous → exactly N rows in DB, count denorm correct.
- Rate limit recovery: 429 → wait → 200.

### Tier 3 — E2E (Playwright, headless on CI, target <60s)

Three critical flows only:
1. Create room → fullscreen QR renders → bookmark link works.
2. Audience: scan URL → enter name → ask → see appear → upvote → see count increment.
3. Presenter: see new question via SSE → pin → audience sees pinned banner → mark answered → audience sees move.

**NOT testing in v1:** visual regression, load testing, browser matrix beyond Chrome + Safari mobile.

---

## 13. Deployment — Railway

```
┌──────────────────────────────────────────────┐
│  Railway service: qa-app                     │
│  ──────────────────────────────────────────  │
│  Image: built from Dockerfile                │
│  Process: uvicorn app.main:app               │
│           --host 0.0.0.0 --port $PORT        │
│           --workers 1                        │
│                                              │
│  Volume mounted at /data                     │
│   └── sqlite.db                              │
│                                              │
│  Env vars:                                   │
│   • APP_BASE_URL                             │
│   • SQLITE_PATH=/data/sqlite.db              │
│   • LOG_LEVEL=INFO                           │
│   • SESSION_SECRET (32-byte random)          │
│   • ROOM_TTL_HOURS=24                        │
│   • EMAIL_PROVIDER=resend                    │
│   • EMAIL_API_KEY (Resend API key)           │
│   • EMAIL_FROM_ADDRESS=qa@dlai.app           │
│   • EMAIL_FROM_NAME="DLAI Q&A"               │
│                                              │
│  Healthcheck: GET /healthz                   │
└──────────────────────────────────────────────┘
```

**Single-worker requirement:** SSE fanout uses an in-process queue. Multiple workers would split the queue and break real-time delivery. Acceptable at ≤50 audience scope. To scale: swap to Redis pub/sub.

**Dockerfile:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**railway.toml:**

```toml
[build]
builder = "DOCKERFILE"

[deploy]
healthcheckPath = "/healthz"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[mounts]]
volumePath = "/data"
```

**Pre-deploy CI checks:**

| Check | Pass criterion |
|-|-|
| `ruff check` | clean |
| `mypy app/` | clean |
| `pytest tests/unit tests/integration` | green |
| `pytest tests/e2e` against built container | green |
| `docker build .` | succeeds |
| Railway preview env smoke | `/healthz` 200 + create-room flow works |

**Observability (v1, cheap):**
- Structured JSON logs (`structlog`) → Railway log drain
- Request middleware: method, path, status, duration_ms, room_code
- No external APM in v1

**Cost:** Railway hobby tier (~$5/mo) covers single service + 1GB volume comfortably for ≤50 audience scope.

---

## 14. Out of scope (explicit)

These are intentionally deferred. Each can be added without a rewrite:

- Persistent presenter accounts / session history
- JSON export (CSV is the only export format in v1)
- Spam, profanity, abuse filters
- CAPTCHA / bot detection
- Multi-presenter roles & permissions
- Threaded replies / comments under questions
- Emoji reactions
- Question editing or deletion by author
- Analytics dashboard
- Visual regression testing
- Load testing infrastructure
- Custom domains per room
- Internationalization

---

## 15. Open questions for the implementation plan

These don't block design approval but should be decided in the first plan step:

1. **HTMX vs Alpine.js for tiny client logic** — HTMX is enough for almost everything (DOM swaps via SSE); Alpine.js would help only with highly interactive presenter shortcuts. Default: **HTMX + ~50 lines vanilla JS**.
2. **Room code generator collision rate** — 6 chars × 32-char alphabet = ~10⁹ codes. At 1000 active rooms, collision probability negligible. Retry on collision (rare), max 3 attempts.
3. **Initial migrations approach** — Alembic vs `metadata.create_all()`. Default: `create_all()` for v1 simplicity, switch to Alembic before v1.1.
4. **QR library specifics** — `qrcode` Python lib for SVG, custom CSS for brand styling. Need to verify SVG output supports per-module CSS classes.
5. **Email provider choice** — Default is **Resend** (cleanest API, generous free tier — 3,000 emails/mo, simple SDK). Alternatives: Postmark, SendGrid, AWS SES. Decide before plan step that wires email.py.
6. **Email job execution model** — FastAPI `BackgroundTasks` (in-process, simplest) vs APScheduler (more robust retry). Default: BackgroundTasks for v1; if delivery reliability matters, swap to APScheduler with persisted job state.
