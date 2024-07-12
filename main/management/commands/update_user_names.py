from django.core.management.base import BaseCommand
from main.models import CustomUser


class Command(BaseCommand):
    help = 'Update user names to remove forced capitalization'

    def handle(self, *args, **kwargs):
        users = CustomUser.objects.all()
        for user in users:
            user.first_name = user.first_name.strip()
            user.last_name = user.last_name.strip()
            user.save(update_fields=['first_name', 'last_name'])
        self.stdout.write(self.style.SUCCESS(
            'Successfully updated user names'))
