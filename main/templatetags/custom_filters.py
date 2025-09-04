from django import template
from django.utils import timezone


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
    iMessage-like timestamp:
      - today → '8:00 AM'
      - this week → 'Monday'
      - older → '8/25/25'
    """
    if not dt:
        return ""
    now = timezone.localtime()
    dt = timezone.localtime(dt)
    if dt.date() == now.date():
        return dt.strftime("%-I:%M %p")  # Linux/macOS strftime
    if (now.date() - dt.date()).days < 7:
        return dt.strftime("%A")
    return dt.strftime("%-m/%-d/%y")
