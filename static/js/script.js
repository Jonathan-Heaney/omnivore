// ---------- intent parsing ----------
const urlParams = new URLSearchParams(location.search);
const FOCUS = urlParams.get('focus'); // "piece" | "thread" | null
const FOCUS_OTHER = urlParams.get('other'); // user id string or null

// Optional: clean the URL once we’ve read intent (prevents re-trigger on refresh)
window.addEventListener('DOMContentLoaded', () => {
  if (FOCUS || FOCUS_OTHER || urlParams.get('n')) {
    history.replaceState({}, '', location.pathname);
  }
});

// ---------- helpers ----------
function getCSRFToken() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function updateNotificationBell(total) {
  const link = document.getElementById('notification-link');
  const icon = document.getElementById('notification-icon');
  const badge = document.getElementById('notif-badge');
  if (!link || !icon || !badge) return;

  const n = Number(total || 0);
  if (n > 0) {
    link.classList.add('has-unread');
    icon.classList.remove('fa-regular');
    icon.classList.add('fa-solid');
    badge.classList.add('notif-badge--count');
    badge.removeAttribute('data-dot');
    badge.textContent = String(n);
  } else {
    link.classList.remove('has-unread');
    icon.classList.remove('fa-solid');
    icon.classList.add('fa-regular');
    badge.classList.remove('notif-badge--count');
    badge.setAttribute('data-dot', '1'); // tiny dot mode
    badge.textContent = '';
  }
}

// Flip header to "read" immediately (idempotent)
function clearUnreadHeader(headerEl) {
  if (!headerEl) return;
  headerEl.classList.remove('thread__header--unread', 'is-unread');
  headerEl.dataset.markedRead = '1';
  headerEl.removeAttribute('data-unread');
  headerEl.closest('article.thread')?.classList.remove('is-unread');
  const badge = headerEl.querySelector(
    '.unread-badge, .thread__unread, .badge-unread'
  );
  if (badge) badge.remove();
}

// POST to server to mark a specific thread read (owner view)
async function markThreadRead(headerEl) {
  if (!headerEl || headerEl.dataset.markedRead === '1') return;

  const piece = headerEl.getAttribute('data-art');
  const other = headerEl.getAttribute('data-recipient');
  const markUrl =
    headerEl.getAttribute('data-mark-url') || '/threads/mark-read/';
  if (!piece || !other || !markUrl) return;

  const body = new URLSearchParams({ piece, other });

  try {
    const resp = await fetch(markUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      },
      body,
      credentials: 'same-origin',
    });

    if (!resp.ok) {
      console.warn('markThreadRead failed:', resp.status);
      return; // don’t flip UI if server didn’t accept
    }

    const data = await resp.json();
    updateNotificationBell(data.unread_total);
    clearUnreadHeader(headerEl); // ✅ only clear after success
  } catch (e) {
    console.error('markThreadRead error:', e);
  }
}

function focusReplyWithoutJump(artPieceId, recipientId) {
  const form = document.querySelector(
    `#thread-${artPieceId}-${recipientId} .thread__form`
  );
  if (!form) return;

  const input = form.querySelector(
    "textarea, input[type='text'], [contenteditable='true']"
  );
  if (input) {
    try {
      input.focus({ preventScroll: true });
    } catch {
      input.focus();
    }
  }

  const article = document.getElementById(
    `thread-${artPieceId}-${recipientId}`
  );
  if (article) {
    article.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
      behavior: 'smooth',
    });
  }

  const msgs = article?.querySelector('.thread__messages');
  if (msgs)
    requestAnimationFrame(() => {
      msgs.scrollTop = msgs.scrollHeight;
    });
}

// Expand/collapse handler wired per thread
function toggleComments(artPieceId, recipientId) {
  const article = document.getElementById(
    `thread-${artPieceId}-${recipientId}`
  );
  if (!article) return;

  const header = document.getElementById(
    `toggle-header-${artPieceId}-${recipientId}`
  );
  const body = article.querySelector('.thread__body');
  const inner = document.getElementById(
    `comments-${artPieceId}-${recipientId}-container`
  );
  const key = `thread-state-${artPieceId}-${recipientId}`;
  const expanded = header?.getAttribute('aria-expanded') === 'true';

  if (expanded) {
    if (body) body.hidden = true;
    if (inner) inner.style.display = 'none';
    article.classList.add('is-collapsed');
    header?.setAttribute('aria-expanded', 'false');
    localStorage.setItem(key, 'collapsed');
  } else {
    if (body) body.hidden = false;
    if (inner) inner.style.display = 'block';
    article.classList.remove('is-collapsed');
    header?.setAttribute('aria-expanded', 'true');
    localStorage.setItem(key, 'expanded');

    // async server update; UI will clear after success inside markThreadRead()
    markThreadRead(header);

    // polite focus/scroll
    requestAnimationFrame(() => focusReplyWithoutJump(artPieceId, recipientId));
  }
}

// ---------- page init ----------
document.addEventListener('DOMContentLoaded', () => {
  const articles = document.querySelectorAll('article.thread[id^="thread-"]');

  articles.forEach((article) => {
    const parts = article.id.split('-'); // "thread-<pieceId>-<recipientId>"
    // guard: IDs like "thread-123-45"
    if (parts.length < 3) return;
    const artPieceId = parts[1];
    const recipientId = parts[2];

    const key = `thread-state-${artPieceId}-${recipientId}`;
    const header = document.getElementById(
      `toggle-header-${artPieceId}-${recipientId}`
    );
    const body = article.querySelector('.thread__body');
    const inner = document.getElementById(
      `comments-${artPieceId}-${recipientId}-container`
    );

    // ---- Decide initial state (priority: intent > saved state) ----
    let shouldExpand = false;
    let shouldFocus = false;

    if (FOCUS === 'piece') {
      shouldExpand = false;
      localStorage.setItem(key, 'collapsed');
    } else if (FOCUS === 'thread') {
      const isTarget = String(recipientId) === String(FOCUS_OTHER || '');
      shouldExpand = isTarget;
      shouldFocus = isTarget;
      localStorage.setItem(key, isTarget ? 'expanded' : 'collapsed');
    } else {
      const state = localStorage.getItem(key);
      shouldExpand = state === 'expanded';
    }

    // ---- Apply state ----
    if (shouldExpand) {
      if (body) body.hidden = false;
      if (inner) inner.style.display = 'block';
      article.classList.remove('is-collapsed');
      header?.setAttribute('aria-expanded', 'true');

      if (shouldFocus) {
        // deep-link target: clear unread immediately and POST
        clearUnreadHeader(header);
        markThreadRead(header);
        requestAnimationFrame(() =>
          focusReplyWithoutJump(artPieceId, recipientId)
        );
      } else if (FOCUS == null && localStorage.getItem(key) === 'expanded') {
        // legacy restore path
        requestAnimationFrame(() =>
          focusReplyWithoutJump(artPieceId, recipientId)
        );
        // if it was unread and we restored expanded, clear + POST too
        if (header?.classList.contains('thread__header--unread')) {
          clearUnreadHeader(header);
          markThreadRead(header);
        }
      }
    } else {
      if (body) body.hidden = true;
      if (inner) inner.style.display = 'none';
      article.classList.add('is-collapsed');
      header?.setAttribute('aria-expanded', 'false');
    }

    // ---- Listeners ----
    header?.addEventListener('click', () =>
      toggleComments(artPieceId, recipientId)
    );
    header?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleComments(artPieceId, recipientId);
      }
    });
  });
});

document.addEventListener('DOMContentLoaded', function () {
  var textareas = document.querySelectorAll('.replyTextArea');
  var buttons = document.querySelectorAll('.sendButton');

  buttons.forEach(function (button) {
    button.disabled = true;
  });

  textareas.forEach(function (textarea, index) {
    textarea.addEventListener('input', function () {
      var button = buttons[index];
      if (textarea.value.trim() !== '') {
        button.disabled = false;
      } else {
        button.disabled = true;
      }
    });
  });

  textareas.forEach((textarea) => {
    textarea.addEventListener('input', () => {
      // Reset height to auto to recalculate the scrollHeight
      textarea.style.height = 'auto';
      // Set height to scrollHeight
      textarea.style.height = `${textarea.scrollHeight}px`;
    });

    // Trigger input event to set the initial height
    textarea.dispatchEvent(new Event('input'));
  });
});

function clearForm(form) {
  form.reset();
  button = form.querySelector('.sendButton');
  button.disabled = true;
}

document.addEventListener('DOMContentLoaded', () => {
  const modalEl = document.getElementById('deleteConfirmModal');
  if (!modalEl) return;

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  const titleEl = document.getElementById('delete-item-title');
  const formEl = document.getElementById('deleteConfirmForm');
  const confirmBtn = formEl?.querySelector('[type="submit"]');

  // Ensure the modal form has a dedicated hidden next input (create if missing)
  let nextInput = formEl.querySelector('input[name="next"]');
  if (!nextInput) {
    nextInput = document.createElement('input');
    nextInput.type = 'hidden';
    nextInput.name = 'next';
    nextInput.id = 'deleteModalNext';
    formEl.appendChild(nextInput);
  }

  // Delegate clicks from any delete button
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.js-open-delete');
    if (!btn) return;

    const url = btn.getAttribute('data-delete-url');
    const title = btn.getAttribute('data-delete-title') || 'this post';

    // 1) Point the modal form at the right endpoint
    formEl.setAttribute('action', url);

    // 2) Resolve the "next" target (prefer inline form's value)
    const inlineForm = btn.closest('form');
    const inlineNext = inlineForm?.querySelector('input[name="next"]')?.value;
    const dataNext = btn.getAttribute('data-next');
    const fallback = location.pathname + location.search;

    nextInput.value = inlineNext || dataNext || fallback;

    // 3) Populate title text
    titleEl.textContent = title;

    // 4) Enable submit (in case a previous submit disabled it)
    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.removeAttribute('data-submitting');
    }

    // Show modal
    modal.show();
  });

  // Optional: guard against double-submits
  formEl.addEventListener('submit', () => {
    if (!confirmBtn) return;
    if (confirmBtn.getAttribute('data-submitting') === '1') return;
    confirmBtn.setAttribute('data-submitting', '1');
    confirmBtn.disabled = true;
  });
});

// Modal handling
document.addEventListener('DOMContentLoaded', function () {
  // Function to open the modal
  function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
  }

  // Function to close the modal
  function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
  }

  // Add event listeners to all open modal links
  document.querySelectorAll('.open-modal').forEach(function (element) {
    element.addEventListener('click', function (event) {
      event.preventDefault(); // Prevent default action that causes scrolling
      const modalId = event.target.getAttribute('data-modal-id');
      openModal(modalId);
    });
  });

  // Add event listeners to all close modal spans
  document.querySelectorAll('.modal .close').forEach(function (element) {
    element.addEventListener('click', function () {
      const modalId = element.getAttribute('data-modal-id');
      closeModal(modalId);
    });
  });

  // Close the modal when clicking outside of the modal content
  window.addEventListener('click', function (event) {
    document.querySelectorAll('.modal').forEach(function (modal) {
      if (event.target == modal) {
        modal.style.display = 'none';
      }
    });
  });
});

// Create password eyes on Login, Sign Up, and Account Settings pages
function addPasswordToggles(selectors) {
  const EYE = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5C6.5 5 2 9.5 2 12s4.5 7 10 7 10-4.5 10-7S17.5 5 12 5zm0 12c-2.8 0-5-2.24-5-5s2.2-5 5-5 5 2.24 5 5-2.2 5-5 5zm0-8a3 3 0 100 6 3 3 0 000-6z"/>
    </svg>`;
  const EYE_SLASH = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3.27 2L2 3.27 5.11 6.4C3.54 7.55 2.27 9.06 2 12c.49 3.95 5.06 7 10 7 2.02 0 3.9-.53 5.47-1.43l3.26 3.26L22 20.73 3.27 2zM12 17c-3.04 0-6.64-1.93-7.66-5 .2-1.06.83-1.98 1.74-2.74l2.19 2.19A4.98 4.98 0 007 12c0 2.76 2.24 5 5 5 .73 0 1.42-.16 2.05-.44l1.51 1.51C14.71 16.69 13.41 17 12 17zm8.66-5c-.22.9-.74 1.8-1.5 2.58-.74.76-1.68 1.38-2.73 1.78l-2.12-2.12c.43-.56.69-1.26.69-2.02a4 4 0 00-4-4c-.76 0-1.46.26-2.02.69L7.52 7.51C8.88 6.92 10.39 6.6 12 6.6c3.04 0 6.64 1.93 7.66 5z"/>
    </svg>`;

  selectors.forEach((sel) => {
    document.querySelectorAll(sel).forEach((input) => {
      if (input.dataset.hasToggle) return; // avoid duplicates
      input.dataset.hasToggle = 'true';

      // Wrap the input in the positioned container our CSS expects
      const wrapper = document.createElement('div');
      wrapper.className = 'pw-field'; // <-- was 'pw-wrap'
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      // Create the eye button
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'pw-toggle';
      btn.setAttribute('aria-label', 'Show password');
      btn.setAttribute('aria-pressed', 'false');
      btn.innerHTML = EYE;
      wrapper.appendChild(btn);

      // Toggle logic
      btn.addEventListener('click', () => {
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        input.classList.toggle('pw-visible', isHidden);
        btn.setAttribute('aria-pressed', String(isHidden));
        btn.setAttribute(
          'aria-label',
          isHidden ? 'Hide password' : 'Show password'
        );
        btn.innerHTML = isHidden ? EYE_SLASH : EYE;
        input.focus({ preventScroll: true });
      });
    });
  });
}

// One DOMContentLoaded + one HTMX hook is enough
document.addEventListener('DOMContentLoaded', () => {
  addPasswordToggles([
    'input.js-password[type="password"]',
    'input.js-password[type="text"]',
  ]);
});

document.body.addEventListener('htmx:afterSwap', () => {
  addPasswordToggles([
    'input.js-password[type="password"]',
    'input.js-password[type="text"]',
  ]);
});

(function () {
  function focusReply() {
    if (location.hash !== '#reply') return;
    // Try immediately
    let el = document.querySelector('#reply textarea, #comment-textarea');
    if (el) {
      el.focus();
      return;
    }
    // Try again after layout settles
    setTimeout(() => {
      el = document.querySelector('#reply textarea, #comment-textarea');
      if (el) el.focus();
    }, 50);
  }

  document.addEventListener('DOMContentLoaded', focusReply);
  window.addEventListener('pageshow', focusReply); // handles back/forward bfcache
})();

// iOS fixer to navigate directly to reply box from Received Art
(function () {
  // Only when we actually intend to land at the reply box.
  var params = new URLSearchParams(location.search);
  var focus = params.get('focus');
  if (focus !== 'thread') return; // <- ignore focus=piece and no focus

  // iOS WebKit (all iPhone/iPad browsers)
  var ua = navigator.userAgent || '';
  var isIOS = /iPad|iPhone|iPod/.test(ua);
  if (!isIOS) return;

  var reply = document.getElementById('reply');
  if (!reply) return;

  var ta = reply.querySelector('textarea');
  if (ta) {
    try {
      ta.focus({ preventScroll: true });
    } catch (e) {
      ta.focus();
    }
  }

  // Ensure the reply area is actually visible once, without smooth scrolling.
  requestAnimationFrame(function () {
    var rect = reply.getBoundingClientRect();
    var headerOffset =
      parseInt(
        getComputedStyle(document.documentElement).getPropertyValue(
          '--nav-offset'
        )
      ) || 50;

    // If clipped above or below viewport, nudge it into view.
    var topNeeded = rect.top - headerOffset - 8; // keep a little air
    var clippedAbove = rect.top - headerOffset < 0;
    var clippedBelow = rect.bottom > window.innerHeight;

    if (clippedAbove || clippedBelow) {
      window.scrollBy({ top: topNeeded, left: 0, behavior: 'auto' });
    }
  });

  // Optional: clean the URL so refreshes don’t re-run the nudge
  try {
    var clean = new URL(location.href);
    clean.searchParams.delete('focus');
    history.replaceState(null, '', clean);
  } catch (_) {}
})();
