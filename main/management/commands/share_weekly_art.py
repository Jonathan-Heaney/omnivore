# main/management/commands/share_weekly_art.py
from django.core.management.base import BaseCommand
from django.core.mail import get_connection
from main.models import CustomUser
from main.services.sharing import share_weekly_to_user


class Command(BaseCommand):
    help = "Share art with all eligible users weekly. Use --dry-run to preview."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--only-email', help='Process only this email (optional)')
        parser.add_argument('--limit', type=int,
                            help='Max users to process (optional)')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        qs = CustomUser.objects.filter(
            receive_art_paused=False, email_on_art_shared=True)
        if opts.get('only_email'):
            qs = qs.filter(email=opts['only_email'])
        if opts.get('limit'):
            qs = qs.order_by('id')[:opts['limit']]

        processed = sent_ok = skipped = failed = 0

        with get_connection() as conn:
            for user in qs.iterator():
                processed += 1
                try:
                    art = share_weekly_to_user(
                        user=user, dry_run=dry, connection=conn)
                    if art:
                        if dry:
                            self.stdout.write(
                                f"[DRY RUN] {user.email} <- '{art.piece_name}' by {art.user.get_full_name()}")
                        else:
                            sent_ok += 1
                            self.stdout.write(
                                f"[SENT] {user.email} <- '{art.piece_name}'")
                    else:
                        skipped += 1
                        self.stdout.write(
                            f"[SKIP] {user.email}: no eligible art or paused")
                except Exception as e:
                    failed += 1
                    self.stderr.write(f"[FAIL] {user.email}: {e}")

        if dry:
            self.stdout.write(self.style.WARNING(
                "Dry run complete. No emails sent."))
        self.stdout.write(self.style.SUCCESS(
            f"Processed={processed}  Sent={sent_ok}  Skipped={skipped}  Failed={failed}"
        ))
