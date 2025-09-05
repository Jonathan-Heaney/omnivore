// Grab CSRF from cookie (Django default cookie name is "csrftoken")
function getCSRFToken() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

async function markThreadRead(headerEl) {
  if (!headerEl || headerEl.dataset.markedRead === '1') return;

  const piece = headerEl.getAttribute('data-art');
  const other = headerEl.getAttribute('data-recipient');

  // Send as application/x-www-form-urlencoded to match request.POST
  const body = new URLSearchParams({ piece, other });

  try {
    const resp = await fetch('/threads/mark-read/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        // NOTE: do NOT set Content-Type manually when using URLSearchParams in fetch;
        // fetch will set it correctly (application/x-www-form-urlencoded;charset=UTF-8)
      },
      body,
      credentials: 'same-origin',
    });

    if (resp.ok) {
      // Optimistically flip the UI
      headerEl.classList.remove('thread__header--unread');
      const b = headerEl.querySelector('.unread-badge');
      if (b) b.remove();
      headerEl.dataset.markedRead = '1';
    } else {
      // Optional: console.debug(await resp.text());
    }
  } catch (e) {
    // Optional: console.debug(e);
  }
}

// --- helper: focus reply field + scroll it into view ---
function focusReply(articleEl) {
  const replyField = articleEl.querySelector(
    '.thread__form textarea, .thread__form input[type="text"], .thread__form [contenteditable="true"]'
  );
  if (!replyField) return;

  // give layout a beat to finish expanding before focusing/scolling
  setTimeout(() => {
    replyField.focus({ preventScroll: true });
    replyField.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, 50);
}

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

    // ✅ mark as read + autofocus on manual expand
    markThreadRead(header);
    focusReply(article);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const articles = document.querySelectorAll('article.thread[id^="thread-"]');

  let didAutoFocus = false; // focus only the first auto-expanded thread

  articles.forEach((article) => {
    const [, artPieceId, recipientId] = article.id.split('-'); // "thread-<piece>-<user>"
    const key = `thread-state-${artPieceId}-${recipientId}`;
    const state = localStorage.getItem(key);

    const header = document.getElementById(
      `toggle-header-${artPieceId}-${recipientId}`
    );
    const body = article.querySelector('.thread__body');
    const inner = document.getElementById(
      `comments-${artPieceId}-${recipientId}-container`
    );

    const shouldExpand = state === 'expanded';

    if (shouldExpand) {
      if (body) body.hidden = false;
      if (inner) inner.style.display = 'block';
      article.classList.remove('is-collapsed');
      header?.setAttribute('aria-expanded', 'true');

      // ✅ mark as read + autofocus on auto-expand (first one only)
      markThreadRead(header);
      if (!didAutoFocus) {
        focusReply(article);
        didAutoFocus = true;
      }
    } else {
      if (body) body.hidden = true;
      if (inner) inner.style.display = 'none';
      article.classList.add('is-collapsed');
      header?.setAttribute('aria-expanded', 'false');
      if (state === null) localStorage.setItem(key, 'collapsed');
    }

    // Click & keyboard toggle
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

function confirmDelete() {
  return confirm(
    'Are you sure you want to delete this post? This cannot be undone.'
  );
}

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
