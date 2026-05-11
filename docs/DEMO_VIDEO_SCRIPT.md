# Demo video script — AskUp ▲

**Target length:** ~90 seconds.
**Recording tool:** [Loom](https://www.loom.com) (free, easiest) or QuickTime → drop into [Gifski](https://gif.ski) for a GIF.
**Resolution:** 1920×1080 minimum. Record at native scale.

This script is structured for one continuous take. If you stumble, just keep going — Loom lets you trim. Aim for "conversational but tight."

---

## Setup (do this once, before you hit record)

1. Open **two browser windows** side-by-side, or one window with two tabs you can flip between with `Cmd+Option+←/→`:
   - **Window A (presenter desktop):** `https://askup.site` — you'll start a session from here
   - **Window B (audience phone-shaped):** a Chrome window resized to ~390×844 to mimic an iPhone, OR an actual phone with the Loom mobile app screen-recording
2. Disable browser notifications and close other tabs to keep the chrome clean.
3. If you're using a phone, AirPlay/Quicktime-mirror it to your desktop so the camera captures it.
4. Plug in headphones to suppress room echo.

---

## Shot list & narration

> **Tip:** Read the narration once aloud before recording. The bracketed `[ACTION]` lines are what you click; the unbracketed lines are what you say.

### Scene 1 — The hook (~10s)

> _"If you've ever run a Q&A at the end of a talk, you know the problem: same loud voices, the same wildcards, no record of what got asked. I built AskUp to fix that — let me show you."_

[ACTION] On Window A, you're on `askup.site`. Mouse hovers near the title.

---

### Scene 2 — Create a session (~10s)

> _"It takes one click. No signup, no account. Type a title if you want."_

[ACTION] Click the title field, type "Demo for Slack."
[ACTION] Click **Start a session →**.

[Window A lands on the share screen with the QR + 6-character code in giant coral type.]

---

### Scene 3 — How the audience joins (~10s)

> _"Now your audience has three ways in. Scan the QR. Type the code at askup.site. Or click the link if you've pasted it in Slack."_

[ACTION] On Window B, type `askup.site/<CODE>` in the URL bar.
[ACTION] Audience page loads. Type "Priya" in the name field.
[ACTION] Click **Continue →**.

---

### Scene 4 — Asking + upvoting (~15s)

> _"Once they're in, they ask. Anyone can upvote. The room votes on what it actually wants to hear answered — the signal beats the loudest voice in the room."_

[ACTION] On Window B, type "How do you handle scale beyond 50 attendees?" and click **Send**.
[ACTION] On Window A, the question card slides into the queue from the top.
[ACTION] On Window B, click the upvote arrow next to the question — coral splash ring radiates out, count flips from 0 to 1.

---

### Scene 5 — Presenter takes control (~20s)

> _"On the presenter side, every question shows up with four buttons — Pin, Done, Hide, Star. When you pin, the audience sees the 'Answering Now' card light up with a coral glow. It's the moment they know to listen."_

[ACTION] On Window A, click **📌 Pin** on the top question.
[Window A: card FLIP-animates from queue into "Answering Now" slot. Coral border + breathing glow appear.]
[Window B: same card appears in the audience's "Answering Now" slot with the coral border.]

> _"When you've answered, click Done. It greys out, drops to the bottom of the queue, gets an 'Answered' badge — and everyone knows you've covered it."_

[ACTION] On Window A, click **✓ Done** on the pinned card.
[Both windows: card sinks, opacity fades to 0.55, "✓ Answered" pill appears.]

---

### Scene 6 — Hide, end, export (~15s)

> _"Hide is for spam or off-topic — it disappears for the audience but stays in your 'Hidden' tab in case of misclick. When you're done, click 'End session.' Audience sees a graceful 'Q&A has ended' page. And you can grab a CSV of every question at any point — during or after."_

[ACTION] On Window A, click **CSV ↓** in the header. Show the CSV briefly in the OS download tray.

---

### Scene 7 — The pitch (~10s)

> _"That's it. It's free. It's at askup.site. Source code is on GitHub. Built with FastAPI, SQLite, and a lot of Motion One animation polish. Try it for your next AMA and tell me how it goes."_

[ACTION] Quick cut to `https://github.com/gauravsurtani/qa-app` README page.
[ACTION] End on the AskUp ▲ logo from the homepage hero.

---

## Total: ~90 seconds.

## Recording tips

- **Speak slightly slower than feels natural.** Recorded audio compresses time perception — what feels slow live often plays back about right.
- **Don't apologize on tape.** If you stumble, pause for two beats and rephrase. You'll cut the pause in Loom.
- **Mouse moves should be deliberate.** Hover near the element for half a beat before clicking — viewers' eyes need that lead time.
- **One screen at a time on display.** Use `Cmd+Tab` between Window A and Window B; don't try to show both side-by-side unless you've got a very wide display. The audience will follow the action better if you cut.
- **Cursor highlight:** macOS Sonoma has a built-in "pointer ring" you can enable in System Settings → Accessibility → Pointer Control → "Shake mouse pointer to locate." Loom also has a built-in cursor highlight option — turn it on.

## After recording

- **Loom:** trim the start + end, share the link in Slack. Loom auto-generates a thumbnail.
- **For a GIF instead:**
  1. Export Loom as `.mp4` (Settings → Download)
  2. Open in [Gifski](https://gif.ski) (free, Mac App Store)
  3. Set quality to 80, FPS 15, width 800px
  4. Result: ~3-5 MB GIF that Slack and GitHub README embed natively

## Where to post

| Platform | Format | Notes |
|-|-|-|
| Slack | Loom link OR `.gif` attachment | Loom link auto-embeds with thumbnail + play button |
| GitHub README | `.gif` embedded with `![Demo](docs/img/demo.gif)` | Keep GIF under 10 MB for fast load |
| LinkedIn | Native upload of `.mp4` | LinkedIn ranks native video over external links |
| Twitter/X | Native upload of `.mp4` (under 2:20) | Auto-loops |
