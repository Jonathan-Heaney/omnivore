from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_templated_email(to_user, subject, template_base, context):
    """
    template_base: e.g. 'emails/comment' -> expects:
      templates/emails/comment.txt
      templates/emails/comment.html (optional)
    """
    ctx = {**context}
    text_body = render_to_string(f"{template_base}.txt", ctx)
    try:
        html_body = render_to_string(f"{template_base}.html", ctx)
    except Exception:
        html_body = None

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL",
                           "no-reply@omnivorearts.com"),
        to=[to_user.email],
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send()
