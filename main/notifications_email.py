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

    # Destination + anchor
    if art_piece.user_id == recipient.id:
        # Recipient owns the piece → My Shared Art, conversation keyed by commenter (sender)
        base_path = "/my-shared-art"
        anchor = f"#comments-{art_piece.id}-{sender.id}-container"
        body_text = (
            f"{sender_full_name} sent you a message about a piece of art you shared: "
        )
    else:
        # Recipient received the piece → My Received Art, single thread per piece
        base_path = "/my-received-art"
        anchor = f"#comments-{art_piece.id}-container"
        body_text = (
            f"{sender_full_name} sent you a message about their piece of art: "
        )
    q = f"?n={notification_id}" if notification_id else ""
    target_url = _abs_url(settings.SITE_URL, f"{base_path}{q}{anchor}")

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

    # CTA: add ?n=<notification_id> if we have one
    path = f"/my-shared-art"
    if notification_id:
        path += f"?n={notification_id}"
    path += f"#art-{art_piece.id}"

    context = {
        "recipient": recipient,
        "liker": liker,
        "art_piece": art_piece,
        "unsubscribe_url": unsubscribe_url,
        "cta_url": _abs_url(settings.SITE_URL, path),
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

    # Link them to My Received Art, scrolled to that piece’s block
    path = "/my-received-art"
    if notification_id:
        path += f"?n={notification_id}"
    path += f"#art-{art_piece.id}"   # matches your template IDs

    context = {
        "recipient": recipient,
        "sender": sender,
        "art_piece": art_piece,
        "cta_url": _abs_url(settings.SITE_URL, path),
        "unsubscribe_url": unsubscribe_url,
    }

    subject = f"{sender.get_full_name()} shared some art with you!"
    send_templated_email(recipient, subject, "emails/shared_art", context)
