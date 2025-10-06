import re
from django.conf import settings

# Match src="/media/..." to make absolute
_ABS_MEDIA_RE = re.compile(r'(<img[^>]+src=)["\']\/media\/', re.IGNORECASE)


def absolutize_media_urls(html: str) -> str:
    base = getattr(settings, "EMAIL_SITE_URL", settings.SITE_URL).rstrip("/")
    # Handles both src="/media/..." and src='/media/...'
    return _ABS_MEDIA_RE.sub(rf'\1"{base}/media/', html)


def normalize_email_images(html: str) -> str:
    """
    Make all <img> tags email-safe & responsive:
    - Remove width/height attributes (Gmail respects them!)
    - Ensure inline style includes: max-width:100%; height:auto; display:block;
    """
    # Remove width/height attributes
    html = re.sub(r'(<img\b[^>]*?)\swidth="[^"]*"',
                  r'\1', html, flags=re.IGNORECASE)
    html = re.sub(r'(<img\b[^>]*?)\sheight="[^"]*"',
                  r'\1', html, flags=re.IGNORECASE)

    # Add or append responsive styles
    def _ensure_style(m):
        tag = m.group(0)
        if re.search(r'\bstyle\s*=', tag, flags=re.IGNORECASE):
            return re.sub(
                r'style="([^"]*)"',
                lambda sm: f'style="{sm.group(1).rstrip(";")};max-width:100%;height:auto;display:block;"',
                tag,
                flags=re.IGNORECASE,
            )
        else:
            # insert before closing >
            return tag[:-1] + ' style="max-width:100%;height:auto;display:block;">'

    html = re.sub(r'<img\b[^>]*?>', _ensure_style, html, flags=re.IGNORECASE)
    return html
