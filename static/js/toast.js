/**
 * Toast notification system — item #3
 * window.showToast(message, kind = 'success')
 * kind: 'success' | 'warning' | 'error'
 * Max 2 visible, auto-dismiss after 3s, slide-in 240ms, fade-out 200ms
 */
(function () {
  let container = null;
  const queue = [];
  const MAX_VISIBLE = 2;
  let visible = 0;

  const COLORS = {
    success: { bg: 'var(--dlai-coral)', text: 'white', icon: '✓' },
    warning: { bg: 'var(--dlai-navy)',  text: 'white', icon: '⚠' },
    error:   { bg: '#DC2626',           text: 'white', icon: '✕' },
  };

  function getContainer() {
    if (container) return container;
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'false');
    container.style.cssText = [
      'position:fixed',
      'bottom:80px',
      'left:50%',
      'transform:translateX(-50%)',
      'z-index:9999',
      'display:flex',
      'flex-direction:column',
      'align-items:center',
      'gap:8px',
      'pointer-events:none',
    ].join(';');
    document.body.appendChild(container);
    return container;
  }

  function dismiss(toast) {
    toast.style.transition = 'opacity 200ms var(--easing-out, ease), transform 200ms var(--easing-out, ease)';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
      visible--;
      if (queue.length > 0) {
        const next = queue.shift();
        show(next.message, next.kind);
      }
    }, 200);
  }

  function show(message, kind) {
    if (visible >= MAX_VISIBLE) {
      queue.push({ message, kind });
      return;
    }
    visible++;
    const c = COLORS[kind] || COLORS.success;
    const toast = document.createElement('div');
    toast.setAttribute('role', 'status');
    toast.style.cssText = [
      `background:${c.bg}`,
      `color:${c.text}`,
      'padding:10px 18px',
      'border-radius:8px',
      'font-size:14px',
      'font-weight:500',
      'display:flex',
      'align-items:center',
      'gap:8px',
      'box-shadow:0 4px 16px rgba(15,23,42,0.18)',
      'opacity:0',
      'transform:translateY(16px)',
      'transition:opacity 240ms ease-out, transform 240ms ease-out',
      'pointer-events:auto',
      'white-space:nowrap',
    ].join(';');

    const iconEl = document.createElement('span');
    iconEl.textContent = c.icon;
    iconEl.style.cssText = 'font-size:13px;font-weight:700;';
    toast.appendChild(iconEl);

    const msgEl = document.createElement('span');
    msgEl.textContent = message;
    toast.appendChild(msgEl);

    getContainer().appendChild(toast);

    // Trigger slide-in
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
      });
    });

    const timer = setTimeout(() => dismiss(toast), 3000);
    toast.addEventListener('click', () => { clearTimeout(timer); dismiss(toast); });
  }

  window.showToast = function (message, kind) {
    show(message, kind || 'success');
  };
})();
