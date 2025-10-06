# blog/tasks.py
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from celery import shared_task

from main.models import CustomUser
from main.utils.email_unsub import make_unsub_token
from .models import BlogPost
from .utils import absolutize_media_urls, normalize_email_images


def _abs_url(base, path):
    return base.rstrip("/") + path


@shared_task
def send_blog_post_email(blog_post_id):
    post = BlogPost.objects.get(id=blog_post_id)

    recipients = CustomUser.objects.filter(
        receive_blog_emails=True
    ).only("id", "email", "first_name", "last_name")

    subject = f"New from Omnivore: {post.title}"

    for user in recipients:
        token = make_unsub_token(user.id, "blog")
        unsubscribe_url = _abs_url(settings.SITE_URL, reverse(
            "email_unsubscribe", args=[token]))

        html = render_to_string(
            "blog/email/blog_post_email.html",
            {
                "post": post,
                "SITE_URL": settings.SITE_URL,   # used by View online
                "unsubscribe_url": unsubscribe_url,  # ✅ now exists during render
            },
        )
        # fix /media → absolute (uses EMAIL_SITE_URL if set)
        html = absolutize_media_urls(html)
        # strip width/height and enforce responsive
        html = normalize_email_images(html)

        msg = EmailMessage(
            subject=subject,
            body=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            headers={
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        msg.content_subtype = "html"
        msg.send(fail_silently=False)
