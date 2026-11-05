"""Preview-only bootstrap primitive. Existing identities are never rewritten."""
from django.contrib.auth import get_user_model
from django.core.management import CommandError
from django.db import transaction
from .access_service import policy_lock
from .rbac import roles


@transaction.atomic
def bootstrap_accounts(read_secret):
    policy_lock()
    User = get_user_model()
    users = list(User.objects.select_for_update().prefetch_related('groups'))
    admins = [user for user in users if 'MAIN_ADMIN' in roles(user)]
    reserved = next((user for user in users if user.username == 'admin'), None)
    if reserved and 'MAIN_ADMIN' not in roles(reserved):
        raise CommandError('Reserved admin username exists without MAIN_ADMIN; operator review required.')
    demo_accounts = [('verify-nutritionist', '시범 영양사', 'NUTRITIONIST'),
                     ('verify-supplier', '시범 공급업체', 'SUPPLIER')]
    missing_demo = [entry for entry in demo_accounts if not any(user.username == entry[0] for user in users)]
    admin_secret = read_secret('preview_admin_password').strip() if not admins else None
    demo_secret = read_secret('demo_password').strip() if missing_demo or not admins else None
    if admin_secret is not None and (not admin_secret or admin_secret == demo_secret):
        raise CommandError('A separate non-empty administrator secret is required. Existing accounts were not changed.')
    if demo_secret is not None and not demo_secret:
        raise CommandError('A non-empty demo secret is required. Existing accounts were not changed.')
    if not admins:
        User.objects.create_superuser('admin', password=admin_secret, name='시범 관리자')
    for username, label, role in missing_demo:
        User.objects.create_user(username, password=demo_secret, name=label, role=role, is_active=True)
    return {'created_admin': not bool(admins), 'created_demo_accounts': len(missing_demo)}
