from django.conf import settings
from django.urls import reverse
from main.utils.email_unsub import make_unsub_token
from .mail import send_templated_email


def _abs_url(base, path):
    # base like https://omnivorearts.com or your staging URL in that env
    return base.rstrip("/") + path


def send_comment_email(*, recipient, comment, notification_id=None):
    if not getattr(recipient, "email_on_comment", False):
        return

    token = make_unsub_token(recipient.id, "comment")
    unsubscribe_url = _abs_url(settings.SITE_URL,
                               reverse("email_unsubscribe", args=[token]))

    art_piece = comment.art_piece
    sender = comment.sender
    sender_full_name = sender.get_full_name()

    # Deep link to art detail, carry ?n=<id> for read tracking
    q = f"?n={notification_id}" if notification_id else ""
    target_url = _abs_url(settings.SITE_URL, reverse(
        "art_detail", args=[art_piece.public_id]) + q)

    if art_piece.user_id == recipient.id:
        body_text = f"<strong>{sender_full_name}</strong> sent you a message on your piece:"
    else:
        body_text = f"<strong>{sender_full_name}</strong> replied to your message on:"

    subject = f"{sender_full_name} sent you a message!"

    context = {
        "recipient": recipient,
        "sender": sender,
        "art_piece": art_piece,
        "comment": comment,
        "target_url": target_url,
        "unsubscribe_url": unsubscribe_url,
        "body_text": body_text,
    }
    send_templated_email(recipient, subject, "emails/comment", context)


def send_like_email(*, recipient, liker, art_piece, notification_id=None):
    """
    Email the owner of an art piece when someone likes it.
    recipient: the owner (art_piece.user)
    liker: the user who clicked like
    art_piece: ArtPiece instance
    notification_id: optional int, used to mark-as-read on click
    """
    if not getattr(recipient, "email_on_like", False):
        return

    # Unsubscribe link
    token = make_unsub_token(recipient.id, "like")
    unsubscribe_url = _abs_url(settings.SITE_URL,
                               reverse("email_unsubscribe", args=[token]))

    q = f"?n={notification_id}" if notification_id else ""
    cta_url = _abs_url(settings.SITE_URL, reverse(
        "art_detail", args=[art_piece.public_id]) + q)

    context = {
        "recipient": recipient,
        "liker": liker,
        "art_piece": art_piece,
        "unsubscribe_url": unsubscribe_url,
        "cta_url": cta_url,
    }

    subject = f"{liker.get_full_name()} loved a piece you shared!"
    send_templated_email(recipient, subject, "emails/like", context)


def send_shared_art_email(*, recipient, sender, art_piece, notification_id=None):
    """
    Email a user when they receive a piece of art.
    recipient: user who received the art (SentArtPiece.user)
    sender:    user who shared the art (art_piece.user)
    """
    # Respect user preference
    if not getattr(recipient, "email_on_art_shared", False):
        return

    # Unsubscribe for this category
    # kinds: "comment", "like", "art"
    token = make_unsub_token(recipient.id, "art")
    unsubscribe_url = _abs_url(
        settings.SITE_URL, reverse("email_unsubscribe", args=[token])
    )

    q = f"?n={notification_id}" if notification_id else ""
    cta_url = _abs_url(settings.SITE_URL, reverse(
        "art_detail", args=[art_piece.public_id]) + q)

    context = {
        "recipient": recipient,
        "sender": sender,
        "art_piece": art_piece,
        "cta_url": cta_url,
        "unsubscribe_url": unsubscribe_url,
    }

    subject = f"{sender.get_full_name()} shared some art with you!"
    subject = f"You have new art from {sender.get_full_name()}!"
    send_templated_email(recipient, subject, "emails/shared_art", context)
