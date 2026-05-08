(function () {
  if (!window.PRESENTER_TOKEN) return;
  const code = window.ROOM_CODE;
  const token = window.PRESENTER_TOKEN;

  function topQuestion() {
    return document.querySelector('#questions-list .q-card');
  }
  async function patch(id, body) {
    return fetch(`/r/${code}/questions/${id}?t=${token}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const top = topQuestion();
    if (!top) return;
    const id = top.dataset.questionId;
    if (e.key === 'p' || e.key === 'P') patch(id, {state: 'pinned'});
    else if (e.key === 'a' || e.key === 'A') patch(id, {state: 'answered'});
    else if (e.key === 'h' || e.key === 'H') patch(id, {state: 'hidden'});
    else if (e.key === 's' || e.key === 'S') patch(id, {starred: true});
  });
})();
