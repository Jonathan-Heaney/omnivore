# main/management/commands/share_weekly_art.py
from django.core.management.base import BaseCommand
from main.models import CustomUser
from main.services.sharing import share_weekly_to_user  # your new service


class Command(BaseCommand):
    help = "Share art with users. Defaults to non-paused users, but can target specific users."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview who would get what without writing or emailing anything.',
        )
        parser.add_argument(
            '--emails',
            nargs='+',
            help='One or more email addresses to target (space-separated).',
        )
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            help='One or more user IDs to target (space-separated).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit the number of users processed (after filtering).',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Confirm sending to everyone that matches filters (guard for non-dry runs).',
        )

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        emails = opts.get('emails') or []
        ids = opts.get('ids') or []
        limit = opts.get('limit')
        all_flag = opts.get('all', False)

        # Base: respect receive_art_paused=False
        qs = CustomUser.objects.filter(receive_art_paused=False)

        if emails:
            qs = qs.filter(email__in=emails)
        if ids:
            qs = qs.filter(id__in=ids)

        # Safety guard: in non-dry runs, require either a target list or --all
        if not dry_run and not emails and not ids and not all_flag:
            self.stderr.write(
                self.style.ERROR(
                    "Refusing to send to the entire cohort. "
                    "Pass --all to confirm, or target users with --emails/--ids."
                )
            )
            return

        if limit:
            qs = qs.order_by('id')[:limit]

        users = list(qs)
        self.stdout.write(
            f"Processing {len(users)} user(s). Dry run: {dry_run}")

        sent = 0
        for u in users:
            piece = share_weekly_to_user(
                user=u, dry_run=dry_run)  # returns ArtPiece | None
            if dry_run:
                if piece:
                    self.stdout.write(
                        f"[DRY RUN] {u.get_full_name()} <- '{piece.piece_name}' by {piece.user}")
                else:
                    self.stdout.write(
                        f"[DRY RUN] {u.get_full_name()} <- (no eligible art)")
            else:
                if piece:
                    sent += 1
                    self.stdout.write(
                        f"[SENT] {u.get_full_name()} <- '{piece.piece_name}' by {piece.artist_name}")
                else:
                    self.stdout.write(
                        f"[SKIP] {u.get_full_name()} — no eligible art")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry run complete. No emails or DB writes."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Shared art with {sent} user(s)."))
