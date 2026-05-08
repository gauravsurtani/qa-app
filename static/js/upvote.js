document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action="upvote"]');
  if (!btn) return;
  e.preventDefault();
  const id = btn.dataset.id;
  const code = window.ROOM_CODE;
  const countEl = btn.querySelector('.upvote-count');
  const wasActive = btn.style.background.includes('245') || btn.style.color === 'white';
  // Optimistic
  countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? -1 : 1));
  btn.classList.add('upvote-active');
  setTimeout(() => btn.classList.remove('upvote-active'), 240);

  try {
    const r = await fetch(`/r/${code}/questions/${id}/upvote`, { method: 'POST' });
    if (!r.ok) throw new Error('upvote failed');
    const body = await r.json();
    countEl.textContent = String(body.upvotes);
    btn.style.background = body.upvoted ? 'var(--dlai-coral)' : 'white';
    btn.style.color = body.upvoted ? 'white' : 'var(--slate-500)';
  } catch (err) {
    countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? 1 : -1));
  }
});
