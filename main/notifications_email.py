from django.conf import settings
from django.urls import reverse
from main.utils.email_unsub import make_unsub_token
from .mail import send_templated_email


def _abs_url(base, path):
    # base like https://omnivorearts.com or your staging URL in that env
    return base.rstrip("/") + path


def send_comment_email(recipient, comment):
    # Respect user preference
    if not getattr(recipient, "email_on_comment", False):
        return

    # Build unsubscribe link
    token = make_unsub_token(recipient.id, "comment")
    unsub_path = reverse("email_unsubscribe", args=[token])
    unsubscribe_url = _abs_url(settings.SITE_URL, unsub_path)

    # (Optional) deep link to the relevant page/anchor
    # If the comment is on recipient's *shared* piece, link to my_shared_art
    # else if it's on a piece they *received*, link to my_received_art.
    # Keep it simple for now:
    target_url = _abs_url(settings.SITE_URL, "/my-shared-art/")

    subject = f"{comment.sender.first_name} sent you a message!"
    context = {
        "recipient": recipient,
        "sender": comment.sender,
        "comment": comment,
        "target_url": target_url,
        "unsubscribe_url": unsubscribe_url,
    }
    send_templated_email(recipient, subject, "emails/comment", context)


def send_like_email(*, recipient, liker, art_piece):
    """
    Email the owner of an art piece when someone likes it.
    recipient: CustomUser who shared the piece (art_piece.user)
    liker: CustomUser who clicked like
    art_piece: ArtPiece instance
    """
    if not getattr(recipient, "email_on_like", False):
        return

    # Unsubscribe link for 'like'
    token = make_unsub_token(recipient.id, "like")
    unsub_path = reverse("email_unsubscribe", args=[token])
    unsubscribe_url = _abs_url(settings.SITE_URL, unsub_path)

    context = {
        "recipient": recipient,
        "liker": liker,
        "art_piece": art_piece,
        "unsubscribe_url": unsubscribe_url,
        # Deep-link back to the relevant page/section
        # (owner sees likes on My Shared Art)
        "cta_url": _abs_url(
            settings.SITE_URL,
            f"/my-shared-art#likes-{art_piece.id}"
        ),
    }

    subject = f"{liker.get_full_name()} loved a piece you shared!"
    send_templated_email(recipient, subject, "emails/like", context)
