/**
 * Custom modal system — replaces browser confirm() / alert()
 * window.showModal({ title, body, confirmLabel, cancelLabel, danger }) → Promise<boolean>
 * window.showAlert({ title, body, closeLabel })                        → Promise<void>
 */
(function () {
  'use strict';

  let _overlay = null;
  let _resolveActive = null;

  function getOverlay() {
    if (_overlay) return _overlay;
    _overlay = document.createElement('div');
    _overlay.id = 'modal-overlay';
    _overlay.setAttribute('role', 'dialog');
    _overlay.setAttribute('aria-modal', 'true');
    _overlay.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:10000',
      'display:flex', 'align-items:center', 'justify-content:center',
      'padding:16px',
      'background:rgba(15,23,42,0)',
      'backdrop-filter:blur(0px)',
      'transition:background 200ms ease, backdrop-filter 200ms ease',
    ].join(';');
    document.body.appendChild(_overlay);
    _overlay.addEventListener('click', (e) => {
      if (e.target === _overlay) _close(false);
    });
    return _overlay;
  }

  function _close(result) {
    const overlay = document.getElementById('modal-overlay');
    if (!overlay) return;
    const card = overlay.querySelector('.modal-card');
    if (card) {
      card.style.transform = 'scale(0.96) translateY(4px)';
      card.style.opacity = '0';
    }
    overlay.style.background = 'rgba(15,23,42,0)';
    overlay.style.backdropFilter = 'blur(0px)';
    setTimeout(() => {
      overlay.innerHTML = '';
      overlay.style.display = 'none';
      if (_resolveActive) {
        _resolveActive(result);
        _resolveActive = null;
      }
    }, 220);
  }

  function _buildCard({ title, body, confirmLabel, cancelLabel, danger, alertOnly }) {
    const card = document.createElement('div');
    card.className = 'modal-card';
    card.style.cssText = [
      'background:white',
      'border-radius:16px',
      'padding:28px 28px 24px',
      'max-width:420px', 'width:100%',
      'box-shadow:0 24px 80px rgba(15,23,42,0.22)',
      'transform:scale(0.96) translateY(8px)',
      'opacity:0',
      'transition:transform 240ms cubic-bezier(0.32,0.72,0,1), opacity 200ms ease',
      'font-family:var(--font-sans,system-ui)',
    ].join(';');

    if (title) {
      const h = document.createElement('h2');
      h.style.cssText = 'margin:0 0 10px;font-size:18px;font-weight:700;color:#0F172A;letter-spacing:-0.3px;';
      h.textContent = title;
      card.appendChild(h);
    }

    if (body) {
      const p = document.createElement('p');
      p.style.cssText = 'margin:0 0 24px;font-size:14px;line-height:1.6;color:#64748B;';
      p.textContent = body;
      card.appendChild(p);
    }

    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:10px;justify-content:flex-end;';

    if (!alertOnly && cancelLabel !== false) {
      const cancelBtn = document.createElement('button');
      cancelBtn.textContent = cancelLabel || 'Cancel';
      cancelBtn.style.cssText = [
        'padding:10px 20px', 'border-radius:10px',
        'background:white', 'border:1.5px solid #E2E8F0',
        'font-size:14px', 'font-weight:600', 'cursor:pointer',
        'color:#334155', 'font-family:inherit',
        'transition:background 120ms ease',
      ].join(';');
      cancelBtn.addEventListener('mouseenter', () => cancelBtn.style.background = '#F8FAFC');
      cancelBtn.addEventListener('mouseleave', () => cancelBtn.style.background = 'white');
      cancelBtn.addEventListener('click', () => _close(false));
      row.appendChild(cancelBtn);
    }

    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = confirmLabel || (alertOnly ? 'OK' : 'Confirm');
    const confirmBg = danger ? '#EE414D' : '#F65B66';
    const confirmHover = danger ? '#DC2626' : '#EE414D';
    confirmBtn.style.cssText = [
      'padding:10px 20px', 'border-radius:10px',
      `background:${confirmBg}`, 'border:none',
      'font-size:14px', 'font-weight:600', 'cursor:pointer',
      'color:white', 'font-family:inherit',
      `transition:background 120ms ease`,
    ].join(';');
    confirmBtn.addEventListener('mouseenter', () => confirmBtn.style.background = confirmHover);
    confirmBtn.addEventListener('mouseleave', () => confirmBtn.style.background = confirmBg);
    confirmBtn.addEventListener('click', () => _close(true));

    // Focus management
    row.appendChild(confirmBtn);
    card.appendChild(row);

    // Trap focus
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { _close(false); return; }
      if (e.key !== 'Tab') return;
      const focusables = Array.from(card.querySelectorAll('button'));
      if (!focusables.length) return;
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    });

    return { card, confirmBtn };
  }

  window.showModal = function ({ title, body, confirmLabel, cancelLabel, danger = false }) {
    return new Promise((resolve) => {
      _resolveActive = resolve;
      const overlay = getOverlay();
      overlay.innerHTML = '';
      overlay.style.display = 'flex';

      const { card, confirmBtn } = _buildCard({ title, body, confirmLabel, cancelLabel, danger, alertOnly: false });
      overlay.appendChild(card);

      // Animate in
      requestAnimationFrame(() => {
        overlay.style.background = 'rgba(15,23,42,0.45)';
        overlay.style.backdropFilter = 'blur(4px)';
        requestAnimationFrame(() => {
          card.style.transform = 'scale(1) translateY(0)';
          card.style.opacity = '1';
          setTimeout(() => confirmBtn.focus(), 10);
        });
      });
    });
  };

  window.showAlert = function ({ title, body, closeLabel } = {}) {
    return new Promise((resolve) => {
      _resolveActive = resolve;
      const overlay = getOverlay();
      overlay.innerHTML = '';
      overlay.style.display = 'flex';

      const { card, confirmBtn } = _buildCard({
        title, body,
        confirmLabel: closeLabel || 'OK',
        cancelLabel: false,
        danger: false,
        alertOnly: true,
      });
      overlay.appendChild(card);

      requestAnimationFrame(() => {
        overlay.style.background = 'rgba(15,23,42,0.45)';
        overlay.style.backdropFilter = 'blur(4px)';
        requestAnimationFrame(() => {
          card.style.transform = 'scale(1) translateY(0)';
          card.style.opacity = '1';
          setTimeout(() => confirmBtn.focus(), 10);
        });
      });
    });
  };

  // Global ESC handler
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _resolveActive) _close(false);
  });
})();
