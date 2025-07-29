from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Like, Notification


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created:
        liker = instance.user
        art_piece = instance.art_piece
        recipient = art_piece.user

        # Avoid notifying yourself
        if liker != recipient:
            Notification.objects.create(
                recipient=recipient,
                sender=liker,
                notification_type='like',
                art_piece=art_piece
            )
