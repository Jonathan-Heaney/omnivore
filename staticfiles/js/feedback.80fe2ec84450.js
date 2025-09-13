// feedback.js
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('open-report');
  const modalEl = document.getElementById('reportModal');
  if (!btn || !modalEl) return;

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    modal.show();
  });

  const form = document.getElementById('reportForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submit = form.querySelector('button[type=submit]');
    submit.disabled = true;

    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        body: new FormData(form),
        credentials: 'same-origin',
      });

      // Try to parse JSON; fall back to text
      const ct = resp.headers.get('content-type') || '';
      const payload = ct.includes('application/json')
        ? await resp.json()
        : { ok: false, error: await resp.text() };

      if (resp.ok && payload.ok) {
        modal.hide();
        form.reset();
        const toastEl = document.getElementById('reportToast');
        if (toastEl) bootstrap.Toast.getOrCreateInstance(toastEl).show();
      } else {
        // Show a friendly message; optional: log payload.error to console
        console.warn('Feedback error:', payload);
        alert(payload.error || 'Could not send report.');
      }
    } catch (err) {
      console.error(err);
      alert('Unexpected error. Please try again.');
    } finally {
      submit.disabled = false;
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('reportForm');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    // Let the backend do its thing normally
    setTimeout(() => {
      const toastEl = document.getElementById('reportToast');
      if (toastEl) {
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
      }
    }, 300); // delay a tick so modal closes first
  });
});
