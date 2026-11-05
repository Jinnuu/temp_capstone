from django.core.management.base import BaseCommand
from accounts.access_service import sync_policy


class Command(BaseCommand):
    help = 'Audit the environment-controlled approval policy without modifying accounts.'

    def handle(self, **options):
        sync_policy()
        self.stdout.write('Approval policy synchronized.')
