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
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json', // 👈 add
      },
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
          // Expect Django form errors serialized under "errors"
          const errors = data?.errors || {};
          // Build a simple error list; you can embellish if you want per-field placement
          const items =
            Object.values(errors)
              .flat()
              .map((err) => `<li class="alert alert-danger mb-2">${err}</li>`)
              .join('') ||
            '<li class="alert alert-danger mb-2">Could not save changes.</li>';
          msg.innerHTML = `<ul class="messages">${items}</ul>`;
          saveBtn.disabled = false;
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

    if (window.addPasswordToggles) {
      window.addPasswordToggles([
        'input[name="old_password"]',
        'input[name="new_password1"]',
        'input[name="new_password2"]',
      ]);
    }
  })();
})();
