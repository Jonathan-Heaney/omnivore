from datetime import datetime
from django.utils import timezone
from .models import ArtPiece, Notification


def notifications_context(request):
    if request.user.is_authenticated:
        return {
            'has_unread_notifications': Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).exists()
        }
    return {}


def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}
    return {
        "unread_notifications_count": Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
    }
