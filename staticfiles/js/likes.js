// --- CSRF helper (Django docs pattern) ---
function getCookie(name) {
  const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return m ? m.pop() : '';
}
const csrftoken = getCookie('csrftoken');

// --- SVG paths (keep these in sync with the template) ---
const HEART_FILLED_PATH =
  'M12 21s-7.35-4.49-9.6-8.28C.96 9.89 2.37 6.5 5.64 6.07 7.52 5.82 9.11 6.7 10 8.01c.89-1.31 2.48-2.19 4.36-1.94 3.27.43 4.68 3.82 3.24 6.65C19.35 16.51 12 21 12 21z';

const HEART_OUTLINE_PATH =
  'M12.1 8.64c-.19-.25-.52-.25-.71 0C9.87 10.47 7 12.24 7 14.88 7 16.59 8.41 18 10.12 18c.98 0 1.87-.47 2.38-1.2.51.73 1.4 1.2 2.38 1.2 1.71 0 3.12-1.41 3.12-3.12 0-2.64-2.87-4.41-4.29-6.24z';

// --- Render helpers ---
function renderHeartIcon(btn, liked) {
  const iconWrap = btn.querySelector('.heart-icon');
  if (!iconWrap) return;

  // Prefer SVG if present
  let svg = iconWrap.querySelector('.heart-svg');
  if (svg) {
    // Replace the single <path> for a crisp toggle
    svg.innerHTML = liked
      ? `<path d="${HEART_FILLED_PATH}"></path>`
      : `<path d="${HEART_OUTLINE_PATH}" fill="none" stroke="currentColor" stroke-width="1.5"></path>`;
    // Hide any fallback emoji if it exists
    const fb = iconWrap.querySelector('.heart-fallback');
    if (fb) fb.style.display = 'none';
    return;
  }

  // Fallback to emoji
  iconWrap.textContent = liked ? '❤️' : '♡';
}

function setLiked(btn, liked) {
  btn.classList.toggle('liked', liked);
  btn.setAttribute('aria-pressed', liked ? 'true' : 'false');
  btn.setAttribute(
    'aria-label',
    liked ? 'Unlike this piece' : 'Like this piece'
  );
  btn.dataset.liked = liked ? 'true' : 'false';

  const text = btn.querySelector('.like-text');
  if (text) text.textContent = liked ? 'Loved' : 'Love';

  renderHeartIcon(btn, liked);
}

// --- Delegate clicks for all like buttons on the page ---
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('button.like-button');
  if (!btn) return;

  const pieceId = btn.dataset.pieceId;
  if (!pieceId) return;

  // Optimistic UI
  const wasLiked = btn.classList.contains('liked');
  setLiked(btn, !wasLiked);
  btn.disabled = true;

  try {
    const res = await fetch(`/api/like/${pieceId}/toggle/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json',
      },
      body: '{}', // no payload needed
    });

    if (!res.ok) throw new Error('Bad response');
    const data = await res.json();

    // If server result differs from optimistic state, reconcile
    if (typeof data.liked === 'boolean' && data.liked !== !wasLiked) {
      setLiked(btn, data.liked);
    }

    // Optional counter support
    const counter =
      btn.parentElement && btn.parentElement.querySelector('.likes-count');
    if (counter && typeof data.likes_count === 'number') {
      counter.textContent = data.likes_count;
    }
  } catch (err) {
    // Revert on failure
    setLiked(btn, wasLiked);
    console.error('Toggle like failed:', err);
  } finally {
    btn.disabled = false;
  }
});

// --- Onload: ensure any server-rendered buttons have correct visual state ---
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('button.like-button').forEach((btn) => {
    const liked =
      btn.dataset.liked === 'true' || btn.classList.contains('liked');
    setLiked(btn, liked);
  });
});
