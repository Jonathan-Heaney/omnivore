// Simple, accessible-ish modal toggle for likes list
(function () {
  const openClass = 'is-open';
  let lastTrigger = null;

  function openModal(modal, trigger) {
    lastTrigger = trigger || null;
    modal.classList.add(openClass);
    modal.setAttribute('aria-hidden', 'false');

    // focus the dialog for screen readers
    const dialog = modal.querySelector('.likes-modal__dialog');
    if (dialog) dialog.focus();
    const btn = modal.querySelector('[data-close-modal]');
    if (btn) btn.setAttribute('aria-label', 'Close dialog');
    // prevent background scroll
    document.documentElement.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    modal.classList.remove(openClass);
    modal.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = '';
    if (lastTrigger) {
      try {
        lastTrigger.focus();
      } catch (_) {}
      lastTrigger = null;
    }
  }

  // Delegate: open
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.likes-more');
    if (!trigger) return;
    const id = trigger.getAttribute('data-modal-id');
    const modal = id && document.getElementById(id);
    if (!modal) return;

    e.preventDefault();
    openModal(modal, trigger);
    trigger.setAttribute('aria-expanded', 'true');
  });

  // Delegate: close (x button or backdrop)
  document.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('[data-close-modal]');
    const backdrop = e.target.classList.contains('likes-modal__backdrop');
    if (!closeBtn && !backdrop) return;

    const modal =
      e.target.closest('.likes-modal') ||
      document.querySelector('.likes-modal.is-open');
    if (!modal) return;

    const triggerId = modal.id;
    const trigger = triggerId
      ? document.querySelector(`.likes-more[data-modal-id="${triggerId}"]`)
      : null;
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    closeModal(modal);
  });

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const modal = document.querySelector('.likes-modal.is-open');
    if (!modal) return;
    const triggerId = modal.id;
    const trigger = triggerId
      ? document.querySelector(`.likes-more[data-modal-id="${triggerId}"]`)
      : null;
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    closeModal(modal);
  });
})();
