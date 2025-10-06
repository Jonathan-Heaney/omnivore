import re
from django.conf import settings

_ABS_MEDIA_RE = re.compile(r'src="/media/', re.IGNORECASE)


def absolutize_media_urls(html: str) -> str:
    return _ABS_MEDIA_RE.sub(f'src="{settings.SITE_URL.rstrip("/")}/media/', html)


def make_email_images_responsive(html: str) -> str:
    # Add inline responsive style to <img> tags missing a style attribute
    return re.sub(
        r'<img(?![^>]*\bstyle=)([^>]*?)>',
        r'<img style="max-width:100%;height:auto;display:block;"\1>',
        html,
        flags=re.IGNORECASE
    )
