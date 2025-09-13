# main/services/sharing.py
from __future__ import annotations

import random
from typing import Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings

from main.models import ArtPiece, SentArtPiece, Notification, CustomUser
from main.notifications_email import send_shared_art_email
from main.views import choose_art_piece


__all__ = ["share_weekly_to_user"]


def share_weekly_to_user(*, user: CustomUser, dry_run: bool = False, connection=None) -> Optional[ArtPiece]:
    """
    Core weekly share unit:
      - decide art
      - persist SentArtPiece(source='weekly') (idempotent)
      - create/get Notification
      - send email synchronously (unless dry_run)
    Returns the ArtPiece if one was selected, else None.
    """
    if getattr(user, "receive_art_paused", False) is True:
        return None

    art = choose_art_piece(user)
    if not art:
        return None

    if dry_run:
        return art

    # Write models idempotently and then send
    with transaction.atomic():
        sent_row, _ = SentArtPiece.objects.get_or_create(
            user=user, art_piece=art, defaults={"source": "weekly"}
        )
        n, _ = Notification.objects.get_or_create(
            recipient=user,
            sender=art.user,
            notification_type="shared_art",
            art_piece=art,
            defaults={
                "message": f"🎁 {art.user.first_name} {art.user.last_name} shared some art with you!"
            },
        )

    # Respect email preference inside the mail helper
    send_shared_art_email(
        recipient=user,
        sender=art.user,
        art_piece=art,
        notification_id=n.id,
        connection=connection,  # reuse external connection if provided
    )

    return art
