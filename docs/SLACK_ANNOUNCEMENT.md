# Slack announcement — copy/paste ready

Paste any of the three versions below into Slack. They use Slack-flavored
formatting (`*bold*`, `_italic_`, `<url|text>` links, ``` for code) so they'll
render correctly with no editing.

---

## Version A — short hook with the "why" (one Slack message) — **recommended**

```
:tada: I built *AskUp* — a free live Q&A tool for talks, AMAs, and events.

*Why I built it:*
We host events and the same friction kept showing up during Q&A:
 • Way too much time spent on questions — and rarely the right ones
 • The same loud voices asking the same wildcards
 • No way to remember what was actually asked once the talk ended
 • No signal for what the _audience_ actually wanted answered

*How AskUp fixes it:*
 • Audience scans a QR or types `askup.site/<code>` — no signup, no app install
 • Everyone's questions land in one feed
 • Audience _upvotes_ the ones they want answered — the room's real signal rises to the top
 • Presenter pins "Answering Now," marks done, or hides irrelevant questions
 • Moderators get power; the audience gets a real voice; nothing gets forgotten
 • Every question is saved + exportable as CSV — you walk away with a record

End result: less wasted time, the questions that _actually mattered_ get answered.

:link: Try it: <https://askup.site|askup.site> → tell your audience: _"askup.site — code XYZ123"_
:open_file_folder: Repo + full design doc: <https://github.com/gauravsurtani/qa-app|gauravsurtani/qa-app>

Built end-to-end this weekend: FastAPI + SQLite + SSE on Railway. No accounts, no fluff.

Made with :heart: by <https://www.linkedin.com/in/gaurav-surtani/|Gaurav>
```

---

## Version B — the build-in-public thread (longer, multi-block)

```
*AskUp ▲ — Live Q&A that rises to the top*  :rocket:

Built a free Slido-style Q&A app this weekend, deployed to <https://askup.site|askup.site>.

*The problem*
I needed a Q&A tool for talks where:
• The audience could join with zero friction (no signup, no app)
• I could see everyone's questions live and pick what to answer
• Upvotes surface what the room actually cares about
• Everything feels instant and looks like a paid SaaS product

*Why not Slido / Mentimeter?* Paywalled, corporate, feel-bad freemium walls.

*How it works*
1. Click "Start a session" → get a QR + 6-char room code (e.g. `XYZ123`)
2. Audience scans or visits `askup.site/XYZ123`, types a name once
3. They ask + upvote questions in real time
4. You pin / mark done / hide / star — audience watches the "Answering Now"
   slot update with a coral breathing glow
5. Download a CSV of every question whenever you want
```

```
*The build process — documented end-to-end*

Every step lives in the repo:
• :brain: <https://github.com/gauravsurtani/qa-app/blob/master/docs/superpowers/specs/2026-05-07-qa-app-design.md|Design spec> — 15 sections, every decision argued
• :clipboard: <https://github.com/gauravsurtani/qa-app/blob/master/docs/superpowers/plans/2026-05-08-qa-app-implementation.md|Implementation plan> — 28 TDD-style tasks
• :ship: 52+ atomic commits, each shipping one task with passing tests

*Stack*
• Backend: FastAPI + async SQLAlchemy on SQLite
• Realtime: Server-Sent Events from an in-process asyncio queue
• Frontend: Jinja2 + HTMX + ~300 lines of vanilla JS — *no React, no build step*
• Animations: Motion One + CSS keyframes, FLIP for layout moves
• Hosting: Railway (Dockerfile, persistent volume) → Hostinger DNS for `askup.site`

*Tests*
75 passing — 35 unit, 37 integration (full HTTP + SSE roundtrips), 3 Playwright
E2E covering the critical paths.

*Try it now*
1. Open <https://askup.site|askup.site>
2. Click "Start a session"
3. Open the room URL on your phone (or send the QR to a colleague)
4. Ask something. Upvote it. Pin it.

Repo: <https://github.com/gauravsurtani/qa-app|github.com/gauravsurtani/qa-app>
Star it if you'd use it for your next talk :star2:
```

---

## Version C — the "I'm hiring my own attention" / lessons-learned version

```
*Shipped: AskUp — a free live Q&A tool for talks* :tada:
<https://askup.site|askup.site> · <https://github.com/gauravsurtani/qa-app|repo>

Built end-to-end in a weekend. Quick brain-dump on what I learned :thread:
```

```
1/ *The brainstorm was the most valuable hour of the whole build.*

I didn't write a single line of code until I'd answered:
• Who's the audience? (zero-signup, mobile-first, ≤50 people)
• How do they identify themselves? (just type a name)
• Public-by-default with presenter moderation, or moderated queue?
• Single presenter vs co-host?
• What happens when the session ends?

Those five answers killed 80% of the scope creep that would have otherwise
crept in during implementation.
```

```
2/ *Server-Sent Events &gt; WebSockets when you only need one-way push.*

The whole real-time layer is an in-process `asyncio.Queue` per room.
Connect, drain, ping every 20s. ~40 lines of code. Browsers reconnect
automatically. No Redis, no pub/sub broker, no scaling math.

If I ever need bi-directional or break the single-worker assumption, swap
in Redis. Until then, this is dead simple.
```

```
3/ *HTMX + ~300 lines of vanilla JS beat any SPA stack for this.*

No React. No bundler. No Vite. Server renders the HTML, SSE pushes deltas,
tiny JS handles optimistic upvotes + FLIP animations for card moves.
First paint is sub-200ms. The "build step" is literally `git push`.

I love React for complex state. For a real-time dashboard with mostly text?
Wildly overkill.
```

```
4/ *Cache-Control is the bug you don't see until your deploy doesn't deploy.*

Spent an hour debugging why a JS fix wasn't taking effect after deploy.
Turned out: no `Cache-Control` header on static files → browsers heuristic-
cached the old JS for hours. Added a tiny middleware:

```python
@app.middleware("http")
async def static_cache_control(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
```

Now every deploy revalidates ETags and ships immediately.
```

```
5/ *Animation is the difference between "works" and "feels alive."*

The functional app shipped at commit ~25/52. The next 27 commits were
polish: FLIP transitions for pinned-card moves, rolling digit counts on
upvotes, coral breathing glow on the answering-now slot, splash ring on
upvote tap, parallax orbs on the homepage, stagger entrance for batched
SSE arrivals.

Motion One (the vanilla version of Framer Motion) made all of this
possible without a build step. Spring easing on every move. Every animation
honors `prefers-reduced-motion`.
```

```
:point_down: Try it: <https://askup.site|askup.site>
:open_file_folder: Repo + full spec + plan: <https://github.com/gauravsurtani/qa-app|gauravsurtani/qa-app>
:speech_balloon: If you use it for a talk, send me a screenshot — I'd love
to see it in the wild.

Made with :heart: by <https://www.linkedin.com/in/gaurav-surtani/|Gaurav Surtani>
```

---

## Tips for posting

- **Pick one version.** Don't paste all three.
- **Replace the `:emoji:` codes** if your Slack workspace uses different ones.
- **Add a screenshot** as a Slack attachment (drag the presenter dashboard PNG
  into the message). Slack will render it inline above your text.
- **For a thread** (Version B or C), paste the first block as the parent
  message, then click "Reply in thread" and paste each subsequent block as a
  reply. Slack's "long post" UI breaks readability after ~600 chars.
- **For a single message** (Version A), all three of those code blocks above
  can stay as one message — Slack handles long messages fine, but the visual
  density of three back-to-back code blocks is ugly.
