from datetime import datetime
from django.utils import timezone
from .models import ArtPiece


def has_submitted_art_this_month(request):
    if request.user.is_authenticated:
        today = timezone.now().date()
        first_day_of_month = timezone.make_aware(
            timezone.datetime(today.year, today.month, 1))
        has_submitted = ArtPiece.objects.filter(
            user=request.user, created_at__gte=first_day_of_month).exists()
        return {'has_submitted_art_this_month': has_submitted}
    return {'has_submitted_art_this_month': False}
