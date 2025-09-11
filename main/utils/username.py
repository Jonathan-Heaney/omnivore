import re
import random
from django.utils.text import slugify


def _clean_base(s: str) -> str:
    s = slugify(s or '')
    return re.sub(r'-+', '-', s).strip('-')


def generate_unique_username(first_name: str, last_name: str, email: str, *, Model):
    bases = []
    b1 = _clean_base(f"{first_name}{last_name}")
    b2 = _clean_base(f"{first_name}-{last_name}")
    b3 = _clean_base((email or '').split('@')[0])
    for b in (b1, b2, b3, 'user'):
        if b and len(b) >= 3:
            bases.append(b)

    tried = set()
    for base in bases:
        for suffix in ['', str(random.randint(100, 999)), str(random.randint(1000, 9999))]:
            handle = f"{base}{suffix}"
            key = handle.lower()
            if key in tried:
                continue
            tried.add(key)
            if not Model.objects.filter(username__iexact=handle).exists():
                return handle

    return f"user{random.randint(10000, 99999)}"
