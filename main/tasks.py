from celery import shared_task
from django.contrib.auth import get_user_model
from .models import ArtPiece
from .notifications_email import send_like_email

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
