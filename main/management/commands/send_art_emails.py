import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import ArtPiece, SentArtPiece, CustomUser
from main.views import choose_art_piece, mark_art_piece_as_sent, send_art_piece_email


class Command(BaseCommand):
    help = "Send art emails to eligible participants"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # Define the start and end dates for the range using timezone-aware datetimes
        start_date = timezone.make_aware(timezone.datetime(2024, 12, 1))
        end_date = timezone.make_aware(timezone.datetime(2024, 12, 31))

        # Check if today's date is within the range
        if start_date.date() <= today <= end_date.date():
            first_day_of_month = timezone.make_aware(
                timezone.datetime(today.year, today.month, 1))

            # Get all users who submitted art this month
            users = CustomUser.objects.filter(
                artpiece__created_at__gte=first_day_of_month
            ).distinct()

            # Manually add specific users based on their email addresses
            # specific_users = CustomUser.objects.filter(
            #     email__in=['mtcc96@gmail.com',
            #                'benleach6@gmail.com']
            # )

            # Combine the QuerySets using the union() method
            # users = users.union(specific_users)

            print(users)

            for user in users:
                send_art_piece_email(user)

            self.stdout.write(self.style.SUCCESS(
                'Successfully sent art emails.'))

        else:
            self.stdout.write(self.style.WARNING(
                f"Today's date {today} is not within the specified range. No emails sent."))
