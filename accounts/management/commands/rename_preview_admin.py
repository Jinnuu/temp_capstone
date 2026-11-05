"""Operator-controlled username transition. Dry run unless --apply is explicit."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.access_service import policy_lock, audit
from accounts.rbac import is_main


class Command(BaseCommand):
    help = 'Inspect a Preview MAIN username transition; apply only after explicit operator approval.'

    def add_arguments(self, parser):
        parser.add_argument('--source', default='verify-admin')
        parser.add_argument('--target', default='admin')
        parser.add_argument('--expected-pk', type=int)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        if not getattr(settings, 'SNP_UI_PREVIEW', False):
            raise CommandError('Preview-only command; no changes made.')
        User = get_user_model()
        source, target = options['source'], options['target']
        User._meta.get_field('username').run_validators(target)
        if source == target:
            raise CommandError('Source and target must differ.')
        if not options['apply']:
            user = User.objects.filter(username=source).first()
            if not user or not is_main(user):
                raise CommandError('Source is not an active MAIN_ADMIN.')
            if User.objects.filter(username=target).exists():
                raise CommandError('Target username already exists; no merge or overwrite allowed.')
            self.stdout.write(f'DRY RUN: PK {user.pk}, {source} -> {target}; password, roles and links preserved. Approval required before --apply.')
            return
        if options['expected_pk'] is None:
            raise CommandError('--apply requires --expected-pk from the approved preflight.')
        with transaction.atomic():
            policy_lock()
            user = User.objects.select_for_update().filter(pk=options['expected_pk']).first()
            if not user or not is_main(user):
                raise CommandError('Expected account is not an active MAIN_ADMIN.')
            if user.username == target and not User.objects.filter(username=source).exists():
                self.stdout.write('Already applied to the expected PK; no changes made.')
                return
            if user.username != source or User.objects.filter(username=target).exists():
                raise CommandError('Account identity or target collision changed; no changes made.')
            count = User.objects.count()
            main_count = sum(is_main(item) for item in User.objects.filter(is_active=True))
            preserved = {name: getattr(user, name) for name in ('password','email','name','phone_number','is_active','is_staff','is_superuser','account_state','rbac_managed','role')}
            group_ids = set(user.groups.values_list('pk', flat=True))
            user.username = target
            user.save(update_fields=['username'])
            user.refresh_from_db()
            if preserved != {name: getattr(user, name) for name in preserved} or group_ids != set(user.groups.values_list('pk', flat=True)):
                raise CommandError('Account attributes changed unexpectedly; transaction rolled back.')
            if User.objects.count() != count or sum(is_main(item) for item in User.objects.filter(is_active=True)) != main_count:
                raise CommandError('Account/admin counts changed unexpectedly; transaction rolled back.')
            audit(None, user, 'account.username_changed', {'username': source}, {'username': target}, reason='operator_approved_username_transition')
        self.stdout.write('Username changed on the same account PK; existing password and privileges preserved.')
