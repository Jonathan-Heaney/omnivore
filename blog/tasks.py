from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from celery import shared_task

from main.models import CustomUser
from main.utils.email_unsub import make_unsub_token
from .models import BlogPost
from .utils import absolutize_media_urls, make_email_images_responsive


def _abs_url(base, path):
    return base.rstrip("/") + path


@shared_task
def send_blog_post_email(blog_post_id):
    post = BlogPost.objects.get(id=blog_post_id)

    # Only users who opted in
    recipients = CustomUser.objects.filter(receive_blog_emails=True).only(
        "id", "email", "first_name", "last_name")

    # Pre-render HTML once (then personalize unsubscribe link per user)
    base_html = render_to_string("blog/email/blog_post_email.html", {
        "post": post,
        "SITE_URL": settings.SITE_URL,   # some templates use it directly
    })
    base_html = absolutize_media_urls(base_html)
    base_html = make_email_images_responsive(base_html)

    subject = f"New from Omnivore: {post.title}"

    for user in recipients:
        # Unsubscribe token for "blog"
        token = make_unsub_token(user.id, "blog")
        unsubscribe_url = _abs_url(settings.SITE_URL, reverse(
            "email_unsubscribe", args=[token]))

        # Personalize unsubscribe link
        html = base_html.replace("{{ unsubscribe_url }}", unsubscribe_url)

        msg = EmailMessage(
            subject=subject,
            body=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            headers={
                # Helps inboxes show a native “Unsubscribe” affordance
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                # Some providers use this to allow one-click HTTP POST; harmless if ignored
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        msg.content_subtype = "html"
        msg.send(fail_silently=False)
