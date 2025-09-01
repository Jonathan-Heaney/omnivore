// account_settings.js
// Behavior for Account Settings page (AJAX save + subtle UX helpers)

(function () {
  // Smooth-scroll to ?section=... once on load, then clean URL
  (function scrollToSectionFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const section = params.get('section');
    if (!section) return;
    const el = document.getElementById(section);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const url = new URL(window.location.href);
    url.searchParams.delete('section');
    window.history.replaceState({}, '', url);
  })();

  // Generic form helpers
  function enableWhenDirty(form, saveBtn, baselineGetter, onDirty) {
    // Turn NodeList into a real Array so .map/.some/etc. work everywhere.
    const inputs = Array.from(form.querySelectorAll('input, select, textarea'));
    const baseline = baselineGetter(inputs);

    function isDirty() {
      return inputs.some((el, i) => {
        if (el.type === 'checkbox' || el.type === 'radio')
          return el.checked !== baseline[i];
        return el.value !== baseline[i];
      });
    }

    form.addEventListener('input', () => {
      const dirty = isDirty();
      saveBtn.disabled = !dirty;
      if (dirty && typeof onDirty === 'function') onDirty();
    });
    form.addEventListener('change', () => {
      const dirty = isDirty();
      saveBtn.disabled = !dirty;
      if (dirty && typeof onDirty === 'function') onDirty();
    });

    return {
      refreshBaseline: () => {
        const current = inputs.map((el) =>
          el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value
        );
        for (let i = 0; i < baseline.length; i++) baseline[i] = current[i];
      },
      inputs,
    };
  }

  async function postFormToJSON(form) {
    const formData = new FormData(form);
    const resp = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData,
    });
    const contentType = resp.headers.get('content-type') || '';
    const isJSON = contentType.includes('application/json');
    const data = isJSON ? await resp.json() : {};
    return { ok: resp.ok, data };
  }

  // ACCOUNT INFO
  (function initAccountInfo() {
    const form = document.getElementById('account-info-form');
    if (!form) return;
    const saveBtn = document.getElementById('save-account-info');
    const msg = document.getElementById('account-info-message-container');

    const { refreshBaseline, inputs } = enableWhenDirty(
      form,
      saveBtn,
      (els) =>
        els.map((el) =>
          el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value
        ),
      () => {
        msg.innerHTML = '';
      }
    );

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      saveBtn.disabled = true;
      try {
        const { ok, data } = await postFormToJSON(form);
        if (ok) {
          msg.innerHTML = `<ul class="messages"><li class="alert alert-success">Account information updated.</li></ul>`;
          refreshBaseline();
        } else {
          saveBtn.disabled = false;
          msg.innerHTML = `<div class="alert alert-danger">Something went wrong. Please try again.</div>`;
        }
      } catch (err) {
        saveBtn.disabled = false;
        msg.innerHTML = `<div class="alert alert-danger">Unexpected error. Please try again.</div>`;
        console.error(err);
      }
    });
  })();

  // ART DELIVERY
  (function initArtDelivery() {
    const form = document.getElementById('art-delivery-form');
    if (!form) return;
    const saveBtn = document.getElementById('save-art-delivery');
    const msg = document.getElementById('art-delivery-message-container');

    // Only one checkbox now, but this scales
    const { refreshBaseline } = enableWhenDirty(
      form,
      saveBtn,
      (els) =>
        els.map((el) =>
          el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value
        ),
      () => {
        msg.innerHTML = '';
      }
    );

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      saveBtn.disabled = true;
      try {
        const { ok, data } = await postFormToJSON(form);
        if (ok) {
          msg.innerHTML = `<div class="alert alert-success">${
            data.message || 'Art delivery preference updated.'
          }</div>`;
          refreshBaseline();
        } else {
          msg.innerHTML = `<div class="alert alert-danger">There was a problem saving your preference.</div>`;
          saveBtn.disabled = false;
        }
      } catch (err) {
        msg.innerHTML = `<div class="alert alert-danger">Unexpected error. Please try again.</div>`;
        saveBtn.disabled = false;
        console.error(err);
      }
    });
  })();

  // EMAIL PREFS
  (function initEmailPrefs() {
    const form = document.getElementById('email-pref-form');
    if (!form) return;
    const saveBtn = document.getElementById('save-email-prefs');
    const msg = document.getElementById('email-message-container');

    const { refreshBaseline } = enableWhenDirty(
      form,
      saveBtn,
      (els) =>
        els.map((el) =>
          el.type === 'checkbox' || el.type === 'radio' ? el.checked : el.value
        ),
      () => {
        msg.innerHTML = '';
      }
    );

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      saveBtn.disabled = true;
      try {
        const { ok, data } = await postFormToJSON(form);
        if (ok) {
          msg.innerHTML = `<div class="alert alert-success">${
            data.message || 'Email preferences updated.'
          }</div>`;
          refreshBaseline();
        } else {
          msg.innerHTML = `<div class="alert alert-danger">There was a problem saving your preferences.</div>`;
          saveBtn.disabled = false;
        }
      } catch (err) {
        msg.innerHTML = `<div class="alert alert-danger">Unexpected error. Please try again.</div>`;
        saveBtn.disabled = false;
        console.error(err);
      }
    });
  })();

  // PASSWORD CHANGE
  (function initPasswordChange() {
    const form = document.getElementById('password-form');
    if (!form) return;
    const saveBtn = document.getElementById('save-password');
    const msg = document.getElementById('password-message-container');

    const oldPassword = form.querySelector('input[name=old_password]');
    const newPassword1 = form.querySelector('input[name=new_password1]');
    const newPassword2 = form.querySelector('input[name=new_password2]');

    function valid() {
      const filled = [oldPassword, newPassword1, newPassword2].every(
        (i) => i.value.trim() !== ''
      );
      const match = newPassword1.value === newPassword2.value;
      return filled && match;
    }

    form.addEventListener('input', () => {
      saveBtn.disabled = !valid();
      if (valid()) msg.innerHTML = '';
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      saveBtn.disabled = true;
      try {
        const { ok, data } = await postFormToJSON(form);
        if (ok) {
          msg.innerHTML = `<div class="alert alert-success">${
            data.message || 'Password changed successfully.'
          }</div>`;
          [oldPassword, newPassword1, newPassword2].forEach(
            (i) => (i.value = '')
          );
        } else {
          // Expect Django form errors serialized under "errors"
          try {
            const errors = JSON.parse(data.errors || '{}');
            const items = Object.values(errors)
              .flatMap((fieldErrors) =>
                fieldErrors.map(
                  (e) => `<li class="alert alert-danger mb-2">${e.message}</li>`
                )
              )
              .join('');
            msg.innerHTML = `<ul class="messages">${
              items ||
              '<li class="alert alert-danger">Could not change password.</li>'
            }</ul>`;
          } catch {
            msg.innerHTML = `<div class="alert alert-danger">Could not change password.</div>`;
          }
          saveBtn.disabled = false;
        }
      } catch (err) {
        msg.innerHTML = `<div class="alert alert-danger">Unexpected error. Please try again.</div>`;
        saveBtn.disabled = false;
        console.error(err);
      }
    });

    // Inline password toggles (eyes)
    addPasswordToggles([
      'input[name="old_password"]',
      'input[name="new_password1"]',
      'input[name="new_password2"]',
    ]);
  })();

  // Password eye toggles
  function addPasswordToggles(selectors) {
    const EYE = `
      <svg viewBox="0 0 24 24" aria-hidden="true" width="20" height="20">
        <path d="M12 5C6.5 5 2 9.5 2 12s4.5 7 10 7 10-4.5 10-7S17.5 5 12 5zm0 12c-2.8 0-5-2.24-5-5s2.2-5 5-5 5 2.24 5 5-2.2 5-5 5zm0-8a3 3 0 100 6 3 3 0 000-6z"/>
      </svg>`;
    const EYE_SLASH = `
      <svg viewBox="0 0 24 24" aria-hidden="true" width="20" height="20">
        <path d="M3.27 2L2 3.27 5.11 6.4C3.54 7.55 2.27 9.06 2 12c.49 3.95 5.06 7 10 7 2.02 0 3.9-.53 5.47-1.43l3.26 3.26L22 20.73 3.27 2zM12 17c-3.04 0-6.64-1.93-7.66-5 .2-1.06.83-1.98 1.74-2.74l2.19 2.19A4.98 4.98 0 007 12c0 2.76 2.24 5 5 5 .73 0 1.42-.16 2.05-.44l1.51 1.51C14.71 16.69 13.41 17 12 17zm8.66-5c-.22.9-.74 1.8-1.5 2.58-.74.76-1.68 1.38-2.73 1.78l-2.12-2.12c.43-.56.69-1.26.69-2.02a4 4 0 00-4-4c-.76 0-1.46.26-2.02.69L7.52 7.51C8.88 6.92 10.39 6.6 12 6.6c3.04 0 6.64 1.93 7.66 5z"/>
      </svg>`;

    selectors.forEach((sel) => {
      document.querySelectorAll(sel).forEach((input) => {
        if (input.dataset.hasToggle) return;
        input.dataset.hasToggle = 'true';

        const wrap = document.createElement('div');
        wrap.className = 'pw-wrap';
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pw-toggle';
        btn.setAttribute('aria-label', 'Show password');
        btn.setAttribute('aria-pressed', 'false');
        btn.innerHTML = EYE;
        wrap.appendChild(btn);

        btn.addEventListener('click', () => {
          const show = input.type === 'password';
          input.type = show ? 'text' : 'password';
          input.classList.toggle('pw-visible', show);
          btn.setAttribute('aria-pressed', String(show));
          btn.setAttribute(
            'aria-label',
            show ? 'Hide password' : 'Show password'
          );
          btn.innerHTML = show ? EYE_SLASH : EYE;
          input.focus({ preventScroll: true });
        });
      });
    });
  }
})();
