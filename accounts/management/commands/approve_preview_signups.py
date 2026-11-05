from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from accounts.models import User
from accounts.rbac import can, approval_mode
from accounts.access_service import classify_signup, change_access


class Command(BaseCommand):
    help = 'Approve explicitly confirmed Preview signup requests; never all inactive users.'

    def add_arguments(self, parser):
        parser.add_argument('--actor', required=True)
        parser.add_argument('--confirmed-signup', nargs='+', required=True)

    def handle(self, **options):
        if not getattr(settings, 'SNP_UI_PREVIEW', False) or approval_mode() != 'auto':
            raise CommandError('Only the auto-approval UI Preview is permitted.')
        actor = User.objects.get(username=options['actor'])
        if not can(actor, 'accounts.manage'):
            raise CommandError('An active administrator is required.')
        changed = 0
        for username in options['confirmed_signup']:
            user = User.objects.get(username=username)
            user, _ = classify_signup(actor, user.pk)
            if user.account_state == 'PENDING':
                _, did_change = change_access(actor, user.pk, state='ACTIVE', reason='operator_confirmed_preview_signup')
                changed += did_change
        self.stdout.write(f'Approved {changed} confirmed signup(s).')
