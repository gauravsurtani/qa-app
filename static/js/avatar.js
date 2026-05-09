/**
 * Deterministic gradient avatars — item #1
 * Hash: name.charCodeAt(0) % palettes.length
 * Appends a 28px circle before the author text on every .muted element
 * that contains an .author span or has the "Asking as:" prefix.
 */
(function () {
  const PALETTES = [
    'linear-gradient(135deg, #F65B66 0%, #EE414D 100%)',  // coral → coral-deep
    'linear-gradient(135deg, #36A3C8 0%, #66CCE8 100%)',  // teal-light → lighter
    'linear-gradient(135deg, #002566 0%, #237B94 100%)',  // navy → teal
    'linear-gradient(135deg, #F65B66 0%, #002566 100%)',  // coral → navy
    'linear-gradient(135deg, #36A3C8 0%, #F65B66 100%)',  // teal-light → coral
    'linear-gradient(135deg, #237B94 0%, #36A3C8 100%)',  // teal → teal-light
  ];

  function gradientForName(name) {
    if (!name) return PALETTES[0];
    const code = name.trim().charCodeAt(0);
    return PALETTES[code % PALETTES.length];
  }

  function createAvatar(name) {
    const initial = (name || '?').trim()[0].toUpperCase();
    const grad = gradientForName(name);
    const el = document.createElement('span');
    el.className = 'q-avatar';
    el.setAttribute('aria-hidden', 'true');
    el.textContent = initial;
    el.style.cssText = [
      'display:inline-flex',
      'align-items:center',
      'justify-content:center',
      'width:20px',
      'height:20px',
      'border-radius:50%',
      `background:${grad}`,
      'color:white',
      'font-size:10px',
      'font-weight:700',
      'flex-shrink:0',
      'vertical-align:middle',
      'margin-right:4px',
      'line-height:1',
    ].join(';');
    return el;
  }

  /** Inject avatar into a .muted element that has an .author child */
  function injectAuthorAvatar(mutedEl) {
    if (mutedEl.querySelector('.q-avatar')) return; // already done
    const authorEl = mutedEl.querySelector('.author');
    if (!authorEl) return;
    const name = authorEl.textContent.trim();
    const avatar = createAvatar(name);
    mutedEl.insertBefore(avatar, mutedEl.firstChild);
  }

  /** Inject avatar into the "Asking as: <name>" banner */
  function injectAskingAsAvatar(mutedEl) {
    if (mutedEl.querySelector('.q-avatar')) return;
    const text = mutedEl.textContent || '';
    if (!text.includes('Asking as')) return;
    const strong = mutedEl.querySelector('strong');
    if (!strong) return;
    const name = strong.textContent.trim();
    const avatar = createAvatar(name);
    mutedEl.insertBefore(avatar, mutedEl.firstChild);
  }

  /** Process all current cards */
  function processAll() {
    document.querySelectorAll('.muted').forEach(el => {
      injectAuthorAvatar(el);
      injectAskingAsAvatar(el);
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', processAll);
  } else {
    processAll();
  }

  // Re-run after each SSE-injected card (question.created fires before card is in DOM,
  // so we observe the questions-list with a MutationObserver)
  const observer = new MutationObserver(() => processAll());
  function attachObserver() {
    const list = document.getElementById('questions-list');
    const pinned = document.getElementById('pinned-slot');
    if (list) observer.observe(list, { childList: true, subtree: true });
    if (pinned) observer.observe(pinned, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachObserver);
  } else {
    attachObserver();
  }

  // Expose for external callers
  window.createAvatar = createAvatar;
})();
