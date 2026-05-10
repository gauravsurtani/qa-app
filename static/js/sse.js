(function () {
  const code = window.ROOM_CODE;
  if (!code) return;

  let backoff = 1000;
  const list = document.getElementById('questions-list');
  const isPresenter = !!window.PRESENTER_TOKEN;

  /* ── FLIP helper — item #2 ───────────────────────────── */
  function flipMove(card, newParent, prepend) {
    const first = card.getBoundingClientRect();
    if (prepend && newParent.firstChild) {
      newParent.insertBefore(card, newParent.firstChild);
    } else {
      newParent.appendChild(card);
    }
    const last = card.getBoundingClientRect();
    const dx = first.left - last.left;
    const dy = first.top - last.top;
    if (dx === 0 && dy === 0) return;
    card.style.transform = `translate(${dx}px, ${dy}px)`;
    card.style.transition = 'transform 0s';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        card.style.transition = 'transform 320ms cubic-bezier(0.32, 0.72, 0, 1)';
        card.style.transform = '';
      });
    });
  }

  /* ── Rolling digit helper — item #5 ─────────────────── */
  function rollCount(el, newValue) {
    if (!el) return;
    const str = String(newValue);
    if (el.textContent === str) return;
    el.classList.remove('digit-arrive');
    el.classList.add('digit-roll');
    setTimeout(() => {
      el.textContent = str;
      el.classList.remove('digit-roll');
      el.classList.add('digit-arrive');
      setTimeout(() => el.classList.remove('digit-arrive'), 120);
    }, 110);
  }

  function appendQuestion(q, isNew) {
    if (!list || document.getElementById('q-' + q.id)) return;
    const tmpl = document.createElement('template');

    if (isPresenter) {
      // Full presenter card with 4 action buttons
      tmpl.innerHTML = `<article class="q-card ${isNew ? 'q-card-new' : ''}" id="q-${q.id}" data-question-id="${q.id}"
        style="background:white;border:1px solid var(--slate-200);border-radius:var(--radius-md);padding:14px;margin-bottom:10px;transition:box-shadow 200ms ease,transform 200ms ease;cursor:default;">
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <div style="width:44px;padding:8px 0;text-align:center;color:var(--slate-700);border:1px solid var(--slate-200);border-radius:var(--radius-sm);flex-shrink:0;">
            <div style="font-size:11px;">▲</div>
            <div class="upvote-count" style="font-size:14px;font-weight:700;">${q.upvote_count}</div>
          </div>
          <div style="flex:1;min-width:0;">
            <p style="margin:0 0 6px;line-height:1.5;word-wrap:break-word;font-size:15px;"></p>
            <div class="muted" style="font-size:12px;margin-bottom:10px;">— <span class="author"></span></div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <button class="btn-secondary action-btn" data-act="state" data-val="pinned" data-id="${q.id}"
                      style="font-size:12px;padding:7px 12px;min-height:32px;border-radius:8px;">📌 Pin</button>
              <button class="btn-secondary action-btn" data-act="state" data-val="answered" data-id="${q.id}"
                      style="font-size:12px;padding:7px 12px;min-height:32px;border-radius:8px;">✓ Done</button>
              <button class="btn-secondary action-btn" data-act="state" data-val="hidden" data-id="${q.id}"
                      style="font-size:12px;padding:7px 12px;min-height:32px;border-radius:8px;">⊘ Hide</button>
              <button class="btn-secondary action-btn" data-act="starred" data-val="toggle" data-id="${q.id}"
                      style="font-size:12px;padding:7px 12px;min-height:32px;border-radius:8px;">⭐ Star</button>
            </div>
          </div>
        </div>
      </article>`;
    } else {
      // Audience card with upvote button only
      tmpl.innerHTML = `<article class="q-card ${isNew ? 'q-card-new' : ''}" id="q-${q.id}" data-question-id="${q.id}"
        style="background:white;border:1px solid var(--slate-200);border-radius:var(--radius-md);padding:14px;margin-bottom:10px;">
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <button class="upvote-btn" data-action="upvote" data-id="${q.id}"
            style="background:white;color:var(--slate-500);border:1px solid var(--slate-200);width:48px;padding:8px 0;display:flex;flex-direction:column;align-items:center;border-radius:var(--radius-sm);">
            <span style="font-size:12px;">▲</span>
            <span class="upvote-count" style="font-size:14px;font-weight:600;">${q.upvote_count}</span>
          </button>
          <div style="flex:1;min-width:0;">
            <p style="margin:0 0 6px;line-height:1.45;word-wrap:break-word;"></p>
            <div class="muted" style="font-size:12px;">— <span class="author"></span></div>
          </div>
        </div>
      </article>`;
    }

    const el = tmpl.content.firstElementChild;
    el.querySelector('p').textContent = q.text;
    el.querySelector('.author').textContent = q.author_name;
    list.prepend(el);
  }

  function updateCount(qid, count) {
    const el = document.querySelector('#q-' + qid + ' .upvote-count');
    rollCount(el, count);
    flipReorderQueue();
  }

  /* ── FLIP reorder when ranks change — item #10 ───────── */
  let _reorderRaf = 0;
  function flipReorderQueue() {
    if (!list) return;
    if (_reorderRaf) return;
    _reorderRaf = requestAnimationFrame(() => {
      _reorderRaf = 0;
      const cards = Array.from(list.querySelectorAll(':scope > .q-card'));
      if (cards.length < 2) return;
      const firstRects = new Map(cards.map(c => [c, c.getBoundingClientRect()]));
      const sorted = cards.slice().sort((a, b) => {
        const av = parseInt(a.querySelector('.upvote-count')?.textContent || '0', 10);
        const bv = parseInt(b.querySelector('.upvote-count')?.textContent || '0', 10);
        if (bv !== av) return bv - av;
        return cards.indexOf(a) - cards.indexOf(b);
      });
      const orderUnchanged = sorted.every((c, i) => c === cards[i]);
      if (orderUnchanged) return;
      sorted.forEach(c => list.appendChild(c));
      sorted.forEach(c => {
        const first = firstRects.get(c);
        const last = c.getBoundingClientRect();
        const dy = first.top - last.top;
        if (dy === 0) return;
        c.style.transform = `translateY(${dy}px)`;
        c.style.transition = 'transform 0s';
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            c.style.transition = 'transform 320ms cubic-bezier(0.32, 0.72, 0, 1)';
            c.style.transform = '';
          });
        });
      });
    });
  }

  function handleEvent(type, data) {
    if (type === 'question.created') appendQuestion(data, true);
    else if (type === 'question.upvoted') updateCount(data.id, data.upvotes);
    else if (type === 'question.state_changed') {
      const card = document.getElementById('q-' + data.id);
      if (!card) return;

      // Apply / strip answered styling
      card.classList.toggle('q-card-answered', data.state === 'answered');

      if (data.state === 'hidden') {
        card.remove();
        return;
      }

      const slot = document.getElementById('pinned-slot');

      if (data.state === 'pinned' && slot) {
        if (slot.contains(card)) return; // already there
        // Move whatever else is in the slot back to queue
        const existing = slot.querySelector('.q-card');
        if (existing && list) {
          existing.classList.remove('q-card-pinned');
          flipMove(existing, list, true);
        } else {
          // Clear any empty-state placeholder text
          const placeholder = slot.querySelector('p.muted');
          if (placeholder) placeholder.remove();
        }
        slot.classList.remove('pinned-slot-empty');
        slot.classList.add('pinned-slot-active');
        card.classList.add('q-card-pinned');
        flipMove(card, slot, false);
        return;
      }

      if (data.state === 'live' && slot && slot.contains(card)) {
        // Un-pin: move back to top of queue
        card.classList.remove('q-card-pinned');
        if (list) flipMove(card, list, true);
        else slot.removeChild(card);
        if (!slot.querySelector('.q-card')) {
          slot.classList.remove('pinned-slot-active');
          slot.classList.add('pinned-slot-empty');
          slot.innerHTML = '<p class="muted" style="margin: 0; font-size: 14px; font-style: italic;">Pin a question to highlight it here.</p>';
        }
        return;
      }

      if (data.state === 'answered') {
        // Answered questions sink to the bottom of the queue regardless of where
        // they came from (slot or anywhere in the list). FLIP animates the move.
        if (slot && slot.contains(card)) {
          card.classList.remove('q-card-pinned');
          if (list) flipMove(card, list, false /* append */);
          if (slot && !slot.querySelector('.q-card')) {
            slot.classList.remove('pinned-slot-active');
            slot.classList.add('pinned-slot-empty');
            slot.innerHTML = '<p class="muted" style="margin: 0; font-size: 14px; font-style: italic;">Pin a question to highlight it here.</p>';
          }
        } else if (list && list.contains(card)) {
          // Move within the queue to the bottom
          flipMove(card, list, false /* append */);
        }
        return;
      }
    }
    else if (type === 'audience.count') {
      const pill = document.getElementById('audience-pill');
      if (pill) {
        // Build dot + count structure if not already done
        let dot = pill.querySelector('.audience-dot');
        let countEl = pill.querySelector('.audience-count-num');
        if (!dot) {
          pill.innerHTML = '';
          dot = document.createElement('span');
          dot.className = 'audience-dot';
          dot.setAttribute('aria-hidden', 'true');
          pill.appendChild(dot);
          countEl = document.createElement('span');
          countEl.className = 'audience-count-num';
          pill.appendChild(countEl);
          const label = document.createElement('span');
          label.textContent = ' listening';
          pill.appendChild(label);
        }
        rollCount(countEl, data.count);
      }
    }
    else if (type === 'room.closed') {
      // Audience reloads to land on the "Q&A ended" page. Presenters stay put —
      // they triggered the close and have a "Download CSV?" modal flow that the
      // reload would otherwise interrupt mid-display. Show them a banner instead.
      if (window.PRESENTER_TOKEN) {
        if (!document.getElementById('ended-banner')) {
          const banner = document.createElement('div');
          banner.id = 'ended-banner';
          banner.style.cssText =
            'background:var(--slate-100);border-bottom:1px solid var(--slate-200);' +
            'padding:10px 16px;text-align:center;font-size:13px;color:var(--slate-700);';
          banner.innerHTML =
            '<strong>Session ended.</strong> Audience can no longer ask. ' +
            'CSV available for 24h.';
          const header = document.querySelector('.app-header');
          if (header && header.parentNode) {
            header.parentNode.insertBefore(banner, header.nextSibling);
          } else {
            document.body.prepend(banner);
          }
        }
        // Disable the End-session button
        const endBtn = document.getElementById('end-session-btn');
        if (endBtn) { endBtn.disabled = true; endBtn.style.opacity = '0.55'; endBtn.textContent = 'Ended'; }
      } else {
        window.location.reload();
      }
    }
  }

  function connect() {
    const es = new EventSource(`/r/${code}/events`);
    es.addEventListener('open', () => { backoff = 1000; });
    ['connected', 'question.created', 'question.upvoted', 'question.state_changed', 'audience.count', 'room.closed', 'ping']
      .forEach(t => es.addEventListener(t, ev => handleEvent(t, JSON.parse(ev.data))));
    es.addEventListener('error', () => {
      es.close();
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 30000);
    });
  }
  connect();
})();
