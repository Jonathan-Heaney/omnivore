(function () {
  // Helper: pick an emoji from data-emoji-pool or default to 🎁
  function ensureEmoji(node) {
    if (node.querySelector('.emoji')) return; // already inserted
    const poolAttr = node.getAttribute('data-emoji-pool') || '🎁';
    const pool = poolAttr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const choice = pool[Math.floor(Math.random() * pool.length)] || '🎁';

    const span = document.createElement('span');
    span.className = 'emoji';
    span.setAttribute('aria-hidden', 'true');
    span.textContent = choice;

    // For screen readers, keep text "New" as is; visual users see emoji + New
    node.insertBefore(span, node.firstChild);
  }

  // Only animate when entering the viewport
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const el = entry.target;
        if (entry.isIntersecting) {
          ensureEmoji(el);
          el.classList.add('in-view');

          // Pick one of these for “delight”—comment out any you don’t want:
          el.classList.add('pulse'); // 2 soft pulses after popping in
          el.classList.add('shimmer'); // one-time gentle sheen

          // Stop observing after first reveal so it doesn’t re-trigger
          io.unobserve(el);
        }
      });
    },
    { threshold: 0.6 }
  );

  // Hook up every “New” badge on the page
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.badge-new').forEach((el) => io.observe(el));
  });

  // If the page comes from BFCache, re-run once (pairs nicely with your pageshow handler)
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      document.querySelectorAll('.badge-new').forEach((el) => {
        // re-observe any that didn’t get processed
        if (!el.classList.contains('in-view')) io.observe(el);
      });
    }
  });
})();
