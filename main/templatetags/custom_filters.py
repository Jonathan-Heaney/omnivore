from django import template
from django.utils import timezone, formats
import sys


register = template.Library()


@register.filter
def dict_get(dictionary, key):
    return dictionary.get(key)


@register.filter
def initials(user):
    """Return 2-letter initials from a User (e.g., 'JS')."""
    f = (getattr(user, "first_name", "") or "").strip()[:1]
    l = (getattr(user, "last_name", "") or "").strip()[:1]
    return (f + l).upper() or "?"


# --- helper: locale-independent 12h time with AM/PM (no periods) ---
def _ampm_time(dt):
    """
    12-hour time like '2:39 PM' regardless of OS/locale.
    Assumes dt is timezone-aware and already in local time.
    """
    hour12 = ((dt.hour + 11) % 12) + 1  # 0->12, 13->1, etc.
    minutes = f"{dt.minute:02d}"
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour12}:{minutes} {ampm}"


@register.filter
def recency_stamp(dt):
    """
    iMessage-ish header stamp:
      • today      → '8:00 AM'
      • same week  → 'Mon'
      • older      → '8/25/25'
    """
    if not dt:
        return ""
    now = timezone.localtime()
    dt = timezone.localtime(dt)

    if dt.date() == now.date():
        return _ampm_time(dt)

    # same ISO week & year
    if (dt.isocalendar().week == now.isocalendar().week
            and dt.isocalendar().year == now.isocalendar().year):
        return dt.strftime("%a")  # Mon/Tue/Wed...

    # M/D/YY without leading zeros on M/D
    return f"{dt.month}/{dt.day}/{dt.strftime('%y')}"


@register.filter
def chat_timestamp(value):
    """
    Chat bubble hover/inline timestamp:
      - Today 2:39 PM
      - Thu 2:39 PM                 (within last 7 days)
      - Mon, Aug 16 at 2:39 PM      (older this year)
      - Oct 17, 2024 at 2:39 PM     (previous years)
    """
    if not value:
        return ""
    now = timezone.localtime()
    dt = timezone.localtime(value)

    t = _ampm_time(dt)

    if dt.date() == now.date():
        return f"Today {t}"

    delta_days = (now.date() - dt.date()).days
    if 0 < delta_days < 7:
        # abbreviated weekday (Mon/Tue/…)
        return f"{dt.strftime('%a')} {t}"

    if dt.year == now.year:
        # Mon, Aug 16 at 2:39 PM
        day_abbr = dt.strftime("%a")
        mon_abbr = dt.strftime("%b")
        return f"{day_abbr}, {mon_abbr} {dt.day}"

    # Oct 17, 2024 at 2:39 PM
    mon_abbr = dt.strftime("%b")
    return f"{mon_abbr} {dt.day}, {dt.year}"
