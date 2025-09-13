// static/js/timezone.js  (replace the existing IIFE body)
(function () {
  try {
    var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!tz) return;

    // Grab raw cookie (if any)
    var m = document.cookie.match(/(?:^|; )tz=([^;]+)/);
    var raw = m ? m[1] : null; // e.g. "America%2FChicago"
    var saved = raw ? decodeURIComponent(raw) : null; // e.g. "America/Chicago"

    var needsRewrite =
      !saved || saved !== tz || (raw && raw.indexOf('%2F') !== -1);

    if (needsRewrite) {
      // write RAW value (no encoding)
      document.cookie = [
        'tz=' + tz,
        'Path=/',
        'Max-Age=' + 60 * 60 * 24 * 365 * 5,
        'SameSite=Lax',
      ].join('; ');

      // persist to user profile (best-effort)
      fetch("{% url 'set_timezone' %}", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':
            (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || '',
        },
        body: JSON.stringify({ timezone: tz }),
      }).catch(function () {});
    }
  } catch (_) {}
})();
