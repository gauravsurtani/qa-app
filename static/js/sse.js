(function () {
  const code = window.ROOM_CODE;
  if (!code) return;

  let backoff = 1000;
  const list = document.getElementById('questions-list');
  const pinned = document.getElementById('pinned-slot');

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
    if (el) el.textContent = String(count);
  }

  function handleEvent(type, data) {
    if (type === 'question.created') appendQuestion(data, true);
    else if (type === 'question.upvoted') updateCount(data.id, data.upvotes);
    else if (type === 'question.state_changed') {
      const card = document.getElementById('q-' + data.id);
      if (data.state === 'hidden' && card) card.remove();
    }
    else if (type === 'audience.count') {
      const el = document.getElementById('audience-pill');
      if (el) el.textContent = `● ${data.count} listening`;
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
