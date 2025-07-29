from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Like, Notification


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if not created:
        return

    sender_user = instance.user
    recipient_user = instance.art_piece.user  # The person who shared the piece

    # Avoid self-notification
    if sender_user == recipient_user:
        return

    Notification.objects.create(
        recipient=recipient_user,
        sender=sender_user,
        notification_type='like',
        message=f"{sender_user} loved a piece of art you shared!",
        art_piece=instance.art_piece
    )
