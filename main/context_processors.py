from datetime import datetime
from django.utils import timezone
from .models import ArtPiece


def has_submitted_art_this_month(request):
    if request.user.is_authenticated:
        now = timezone.now()
        first_day_of_month = datetime(
            now.year, now.month, 1)
        has_submitted = ArtPiece.objects.filter(
            user=request.user, created_at__gte=first_day_of_month).exists()
        return {'has_submitted_art_this_month': has_submitted}
    return {'has_submitted_art_this_month': False}
