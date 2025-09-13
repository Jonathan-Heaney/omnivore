from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist


def send_templated_email(
    to_user,
    subject,
    template_base,
    context,
    *,
    unsubscribe_url: str | None = None,
    reply_to: list[str] | None = None,
    bcc: list[str] | None = None,
    fail_silently: bool = False,
    connection=None,
):
    """
    template_base: e.g. 'emails/comment' -> expects:
      templates/emails/comment.txt  (required)
      templates/emails/comment.html (optional)
    """
    # allow passing either a user or an email string
    to_email = getattr(to_user, "email", None) or str(to_user)

    ctx = {**context}
    text_body = render_to_string(f"{template_base}.txt", ctx)

    try:
        html_body = render_to_string(f"{template_base}.html", ctx)
        if html_body and not html_body.strip():
            html_body = None
    except TemplateDoesNotExist:
        html_body = None

    headers = {}
    if unsubscribe_url:
        # Many providers recognize this and surface a native “Unsubscribe”
        headers["List-Unsubscribe"] = f"<{unsubscribe_url}>"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,  # plain text body first
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL",
                           "oliver@omnivorearts.com"),
        to=[to_email],
        bcc=bcc,
        reply_to=reply_to,
        headers=headers or None,
        connection=connection,
    )

    if html_body:
        # adds multipart/alternative
        msg.attach_alternative(html_body, "text/html")

    msg.send(fail_silently=fail_silently)
