from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Like, Notification, Comment, SentArtPiece
from .notifications_email import send_comment_email, send_like_email, send_shared_art_email


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if not created:
        return

    sender_user = instance.user
    recipient_user = instance.art_piece.user  # The person who shared the piece

    # Avoid self-notification
    if sender_user == recipient_user:
        return

    n = Notification.objects.create(
        recipient=recipient_user,
        sender=sender_user,
        notification_type='like',
        message=f"{sender_user} loved a piece of art you shared!",
        art_piece=instance.art_piece
    )

    send_like_email(recipient=recipient_user,
                    liker=sender_user, art_piece=instance.art_piece, notification_id=n.id)


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if not created:
        return

    sender_user = instance.sender
    recipient_user = instance.recipient

    # Avoid self-notification
    if sender_user == recipient_user:
        return

    n = Notification.objects.create(
        recipient=recipient_user,
        sender=sender_user,
        notification_type='comment',
        message=f"{sender_user} sent you a message!",
        art_piece=instance.art_piece
    )

    send_comment_email(recipient=recipient_user,
                       comment=instance, notification_id=n.id)


@receiver(post_save, sender=SentArtPiece)
def create_sent_art_notification(sender, instance, created, **kwargs):
    if not created:
        return

    if created:
        recipient = instance.user
        sender_user = instance.art_piece.user
        art_piece = instance.art_piece

        # Don’t send a notification if the user received their own art
        if recipient == sender_user:
            return

        n = Notification.objects.create(
            recipient=recipient,
            sender=sender_user,
            notification_type='shared_art',
            art_piece=art_piece,
            message=f"{sender_user.first_name} {sender_user.last_name} shared some art with you!"
        )

        # fire the email (respects recipient.email_on_art_shared)
        send_shared_art_email(
            recipient=recipient,
            sender=sender_user,
            art_piece=art_piece,
            notification_id=n.id
        )
