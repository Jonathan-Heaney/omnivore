from celery import shared_task
from django.contrib.auth import get_user_model
from .models import ArtPiece, Comment
from .notifications_email import (
    send_like_email,
    send_comment_email,
    send_shared_art_email,
)

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_like_email_task(self, *, recipient_id, liker_id, art_piece_id, notification_id=None):
    try:
        recipient = User.objects.get(id=recipient_id)
        liker = User.objects.get(id=liker_id)
        art_piece = ArtPiece.objects.get(id=art_piece_id)
        send_like_email(
            recipient=recipient,
            liker=liker,
            art_piece=art_piece,
            notification_id=notification_id,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_comment_email_task(self, *, recipient_id, comment_id, notification_id=None):
    """
    Fire comment notification email to recipient for a specific comment.
    """
    try:
        recipient = User.objects.get(id=recipient_id)
        comment = Comment.objects.select_related(
            "art_piece", "sender", "recipient").get(id=comment_id)
        send_comment_email(
            recipient=recipient,
            comment=comment,
            notification_id=notification_id,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_shared_art_email_task(self, *, recipient_id, sender_id, art_piece_id, notification_id=None):
    """
    Fire “shared art” notification email to the recipient.
    """
    try:
        recipient = User.objects.get(id=recipient_id)
        sender = User.objects.get(id=sender_id)
        art_piece = ArtPiece.objects.get(id=art_piece_id)
        send_shared_art_email(
            recipient=recipient,
            sender=sender,
            art_piece=art_piece,
            notification_id=notification_id,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
