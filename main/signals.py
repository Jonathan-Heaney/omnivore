from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .tasks import (
    send_like_email_task,
    send_comment_email_task,
    send_shared_art_email_task,
)  # Celery tasks
from .models import Like, Notification, Comment, SentArtPiece


@receiver(post_save, sender=Like)
def on_like_created(sender, instance, created, **kwargs):
    if not created:
        return

    liker = instance.user
    recipient = instance.art_piece.user
    art_piece = instance.art_piece

    # Avoid self-notification
    if liker == recipient:
        return

    # Create in-app notification (same as before, but message a bit cleaner)
    n = Notification.objects.create(
        recipient=recipient,
        sender=liker,
        notification_type="like",
        art_piece=art_piece,
        message=f"❤️ {liker.first_name} {liker.last_name} loved a piece you shared: {art_piece.piece_name}"
    )

    # Enqueue the email AFTER the transaction commits successfully
    transaction.on_commit(lambda: send_like_email_task.delay(
        recipient_id=recipient.id,
        liker_id=liker.id,
        art_piece_id=art_piece.id,
        notification_id=n.id,
    ))


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if not created:
        return

    sender_user = instance.sender
    recipient_user = instance.recipient
    art_piece = instance.art_piece
    sender_full_name = sender_user.get_full_name()

    # Avoid self-notification
    if sender_user == recipient_user:
        return

    if art_piece.user_id == recipient_user.id:
        message = f"💬 {sender_full_name} sent you a message on your piece: {art_piece.piece_name}"
    else:
        message = f"💬 {sender_full_name} replied to your message on: {art_piece.piece_name}"

    n = Notification.objects.create(
        recipient=recipient_user,
        sender=sender_user,
        notification_type='comment',
        message=message,
        art_piece=art_piece
    )

    # enqueue email after DB commit
    transaction.on_commit(lambda: send_comment_email_task.delay(
        recipient_id=recipient_user.id,
        comment_id=instance.id,
        notification_id=n.id,
    ))


@receiver(post_save, sender=SentArtPiece)
def create_sent_art_notification(sender, instance, created, **kwargs):
    if not created:
        return

    # Skip notifications for welcome and reciprocal art sharing
    if instance.source in {"welcome", "reciprocal"}:
        return

    recipient = instance.user
    sender_user = instance.art_piece.user
    art_piece = instance.art_piece

    if recipient == sender_user:
        return

    n = Notification.objects.create(
        recipient=recipient,
        sender=sender_user,
        notification_type='shared_art',
        art_piece=art_piece,
        message=f"🎁 {sender_user.first_name} {sender_user.last_name} shared some art with you!"
    )

    transaction.on_commit(lambda: send_shared_art_email_task.delay(
        recipient_id=recipient.id,
        sender_id=sender_user.id,
        art_piece_id=art_piece.id,
        notification_id=n.id,
    ))
