# Lessons learned — building AskUp

Notes I wish someone had handed me before I started. Five lessons from going
brainstorm → spec → plan → ship in a weekend.

---

## 1. The brainstorm was the most valuable hour of the whole build

I didn't write a single line of code until I'd answered five questions:

- **Who's the audience?** ≤50 people, mobile-first, zero signup.
- **How do they identify themselves?** Just type a name. No email, no OAuth.
- **Visibility model?** Public-by-default with presenter moderation (not a moderated queue with approval gates).
- **Single presenter vs co-host?** Single. Bookmark the URL — anyone with it is the host.
- **What happens when the session ends?** Audience sees a graceful "Q&A has ended" page; presenter can still grab the CSV for 24h.

Those five answers killed 80% of the scope creep that would have otherwise crept in during implementation. The
[design spec](superpowers/specs/2026-05-07-qa-app-design.md) is the artifact —
15 sections, every decision argued.

**Takeaway:** the time spent _not_ coding is the time that decides whether the
thing you ship is the thing you wanted to ship.

---

## 2. Server-Sent Events beat WebSockets when you only need one-way push

The whole real-time layer is an in-process `asyncio.Queue` per room. Connect,
drain, ping every 20s. About 40 lines of code in
[`app/services/pubsub.py`](../app/services/pubsub.py) and
[`app/routes/events.py`](../app/routes/events.py).

Browsers reconnect automatically on disconnect — built into the
`EventSource` API. No Redis. No pub/sub broker. No "horizontal scaling"
math.

If I ever need bi-directional traffic or break the single-worker assumption,
swap in Redis. Until then, this is dead simple and survives Railway restarts
because clients re-fetch state and pick up where they left off.

**Takeaway:** WebSockets are the default reach for "real-time," but they're
overkill when traffic flows server → client. SSE is HTTP + a long-lived
response stream — cache layers, proxies, and reconnect logic all just work.

---

## 3. HTMX + ~300 lines of vanilla JS beat any SPA stack for this

No React. No bundler. No Vite. The server renders the HTML; SSE pushes
deltas; tiny JS handles optimistic upvotes + FLIP animations for card moves.
First paint is sub-200ms. The "build step" is literally `git push`.

I love React for complex shared state. But for a real-time dashboard with
mostly text? Wildly overkill. The FastAPI process emits the page,
**Motion One** runs the animations, and the same handler I'd write in a
React `useEffect` lives in 4 lines of vanilla in
[`static/js/sse.js`](../static/js/sse.js).

**Takeaway:** "JS framework" is not the same as "interactivity." If your
state lives mostly on the server, your client can stay tiny.

---

## 4. Cache-Control is the bug you don't see until your deploy doesn't deploy

I spent an hour debugging why an SSE fix wasn't taking effect after deploy.
Browsers were running the OLD `sse.js`. Why?

Railway's edge served only `ETag` + `Last-Modified` — no `Cache-Control`
header. Browsers fell back to RFC 7234 heuristic caching and held onto stale
JS for hours. Even hard-refresh didn't dislodge it because the cached entry
hadn't expired yet by their heuristic clock.

The fix is a 5-line middleware:

```python
@app.middleware("http")
async def static_cache_control(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
```

`no-cache` doesn't mean "don't cache." It means "cache, but **revalidate
ETag on every request.**" Tiny overhead (a 304 round-trip). Massive reliability win.

Belt-and-suspenders: every static asset href in templates also carries a
`?v=N` query string that bumps on each polish pass. Combined, the browser
gets fresh bytes the moment a deploy lands.

**Takeaway:** if your fix is in `git log` but isn't on the user's screen,
suspect cache before you suspect a real bug. Set explicit `Cache-Control`
on every static-asset endpoint.

---

## 5. Animation is the difference between "works" and "feels alive"

The functional app shipped at commit ~25 of 60. The next 35 commits were polish.

What changed in those polish passes:

- **FLIP transitions** when a question moves to the pinned slot or re-ranks after an upvote
- **Rolling-digit counts** when upvote totals change
- **Coral breathing glow** on the "Answering Now" pinned card (3.5s `box-shadow` pulse loop)
- **Splash ring** that radiates from the upvote button on tap
- **Parallax orbs** on the homepage that drift to mouse-move
- **Staggered entrance** when several questions arrive within 200ms of each other
- **Spring easing** (`cubic-bezier(0.32, 0.72, 0, 1)`) on every move
- **`prefers-reduced-motion` collapse to 100ms opacity fades** on every keyframe

Motion One (the vanilla equivalent of Framer Motion, ~4 KB) made all of this
possible without adding a build step. The CSS does most of the work; JS
handles the spatial transitions (FLIP) and one-shot bursts.

**Takeaway:** the user can't tell you why a paid SaaS tool _feels_ different
from an open-source clone — but it almost always comes down to micro-motion.
Budget the polish time as a first-class line item, not a "nice to have."

---

## Bonus — the two questions I'd ask again at the start

Before I started, the spec had me decide:

1. **What gets cut from v1?** Comments, threading, edit-your-own, accounts, analytics, multi-presenter, i18n. Saying these "no" early let v1 be focused.

2. **What's the verbal pitch?** "askup.site — code XYZ123." Five syllables + six characters. Designing _toward_ that pitch made the homepage layout (giant code, big QR, copy-link button) basically write itself.

Both questions are about constraint. Constraint is where good design comes from.
