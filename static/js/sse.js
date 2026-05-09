(function () {
  const code = window.ROOM_CODE;
  if (!code) return;

  let backoff = 1000;
  const list = document.getElementById('questions-list');
  const pinned = document.getElementById('pinned-slot');

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
    const el = tmpl.content.firstElementChild;
    el.querySelector('p').textContent = q.text;
    el.querySelector('.author').textContent = q.author_name;
    list.prepend(el);
  }

  function updateCount(qid, count) {
    const el = document.querySelector('#q-' + qid + ' .upvote-count');
    rollCount(el, count);
  }

  function handleEvent(type, data) {
    if (type === 'question.created') appendQuestion(data, true);
    else if (type === 'question.upvoted') updateCount(data.id, data.upvotes);
    else if (type === 'question.state_changed') {
      const card = document.getElementById('q-' + data.id);
      if (!card) return;
      if (data.state === 'hidden') {
        card.remove();
      } else if (data.state === 'pinned') {
        const slot = document.getElementById('pinned-slot');
        if (slot) {
          slot.innerHTML = '';
          card.classList.remove('q-card-new');
          flipMove(card, slot, false);
        }
      } else if (data.state === 'live') {
        const slot = document.getElementById('pinned-slot');
        if (slot && slot.contains(card)) {
          if (list) flipMove(card, list, true);
          else slot.removeChild(card);
        }
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
      window.location.reload();
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
