document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action="upvote"]');
  if (!btn) return;
  e.preventDefault();
  const id = btn.dataset.id;
  const code = window.ROOM_CODE;
  const countEl = btn.querySelector('.upvote-count');

  // Determine current state by looking at applied background (set after server ack)
  const wasActive = btn.style.background.includes('245') ||
                    btn.style.background.includes('246') ||
                    btn.style.color === 'white';

  // Optimistic count update
  countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? -1 : 1));

  // Scale pulse
  btn.classList.add('upvote-active');
  setTimeout(() => btn.classList.remove('upvote-active'), 280);

  // Radial splash — only when toggling ON; skip in reduced-motion
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!wasActive && !prefersReduced) {
    const splash = document.createElement('div');
    splash.className = 'upvote-splash-ring';
    btn.appendChild(splash);
    setTimeout(() => { if (splash.parentNode) splash.remove(); }, 420);
  }

  try {
    const r = await fetch(`/r/${code}/questions/${id}/upvote`, { method: 'POST' });
    if (!r.ok) throw new Error('upvote failed');
    const body = await r.json();
    countEl.textContent = String(body.upvotes);
    btn.style.background = body.upvoted ? 'var(--dlai-coral)' : 'white';
    btn.style.color      = body.upvoted ? 'white' : 'var(--slate-500)';
  } catch (_err) {
    // Revert optimistic update
    countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + (wasActive ? 1 : -1));
  }
});
