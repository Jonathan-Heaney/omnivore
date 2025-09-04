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


@register.filter
def recency_stamp(dt):
    """
    iMessage-like timestamp for an aware datetime:
      • today        → '8:00 AM'
      • same week    → 'Monday'
      • older        → '8/25/25'
    """
    if not dt:
        return ""

    # ensure both in local tz
    now = timezone.localtime()
    dt = timezone.localtime(dt)

    # Windows doesn't support %-I / %-m / %-d
    WIN = sys.platform.startswith("win")
    fmt_time = "%#I:%M %p" if WIN else "%-I:%M %p"
    fmt_mdyy = "%#m/%#d/%y" if WIN else "%-m/%-d/%y"

    if dt.date() == now.date():
        return dt.strftime(fmt_time)

    # “same week” = same ISO week & year; this matches Messages behavior
    if (dt.isocalendar().week == now.isocalendar().week
            and dt.isocalendar().year == now.isocalendar().year):
        return dt.strftime("%A")

    return dt.strftime(fmt_mdyy)


@register.filter
def chat_timestamp(value):
    """
    Human chat-style timestamp:
      - Today 2:39 p.m.
      - Thursday 2:39 p.m.            (within last 7 days)
      - Mon, Aug 16 at 2:39 p.m.      (older this year)
      - Oct 17, 2024 at 2:39 p.m.     (previous years)
    """
    if not value:
        return ""
    now = timezone.localtime(timezone.now())
    dt = timezone.localtime(value)

    if dt.date() == now.date():
        # Today 2:39 p.m.
        return f"Today {formats.date_format(dt, 'P')}"

    delta_days = (now.date() - dt.date()).days
    if 0 < delta_days < 7:
        # Thursday 2:39 p.m.
        return f"{formats.date_format(dt, 'l')} {formats.date_format(dt, 'P')}"

    if dt.year == now.year:
        # Mon, Aug 16 at 2:39 p.m.
        return f"{formats.date_format(dt, 'D')}, {formats.date_format(dt, 'M j')} at {formats.date_format(dt, 'P')}"

    # Oct 17, 2024 at 2:39 p.m.
    return f"{formats.date_format(dt, 'M j, Y')} at {formats.date_format(dt, 'P')}"
