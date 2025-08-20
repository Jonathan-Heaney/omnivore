from django.core.management.base import BaseCommand
from main.models import CustomUser
from main.views import share_art_piece


class Command(BaseCommand):
    help = "Share art with all eligible users"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview which users would receive which art pieces, without sending or writing anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        eligible_users = CustomUser.objects.filter(receive_art_paused=False)

        shared_count = 0

        for user in eligible_users:
            result = share_art_piece(user, dry_run=dry_run)

            if dry_run:
                if result:
                    self.stdout.write(
                        f"[DRY RUN] {user.get_full_name()} would receive '{result.piece_name}' by {result.artist_name}."
                    )
                else:
                    self.stdout.write(
                        f"[DRY RUN] {user.get_full_name()} would receive nothing (no eligible art)."
                    )
            else:
                if result:
                    shared_count += 1
                    self.stdout.write(
                        f"[SENT] {user.get_full_name()} received '{result.piece_name}' by {result.artist_name}."
                    )
                else:
                    self.stdout.write(
                        f"[SKIP] {user.get_full_name()} — no eligible art."
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry run complete. No art was actually sent."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Shared art with {shared_count} users."))
