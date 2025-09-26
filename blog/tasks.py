from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from main.models import CustomUser
from .models import BlogPost

from celery import shared_task


@shared_task
def send_blog_post_email(blog_post_id):
    post = BlogPost.objects.get(id=blog_post_id)
    subscribers = CustomUser.objects.filter(
        receive_blog_emails=True)  # You may need to add this field

    for user in subscribers:
        html_message = render_to_string("blog/email/blog_post_email.html", {
            "user": user,
            "post": post,
        })

        send_mail(
            subject=f"New from Omnivore: {post.title}",
            message="View this email in HTML format.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
