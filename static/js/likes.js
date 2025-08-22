// --- CSRF helper (Django docs pattern) ---
function getCookie(name) {
  const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return m ? m.pop() : '';
}
const csrftoken = getCookie('csrftoken');

// --- UI helpers ---
function setLiked(btn, liked) {
  btn.classList.toggle('liked', liked);
  btn.setAttribute('aria-pressed', liked ? 'true' : 'false');

  const heart = btn.querySelector('.heart-icon');
  const text = btn.querySelector('.like-text');
  if (heart) heart.textContent = liked ? '❤️' : '♡';
  if (text) text.textContent = liked ? 'Loved' : 'Love';
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
    if (data.liked !== !wasLiked) setLiked(btn, data.liked);

    // Optional: update a local likes counter if you render one
    const counter = btn.parentElement.querySelector('.likes-count');
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
