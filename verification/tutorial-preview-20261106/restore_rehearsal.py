"""Rename/seed/policy rehearsal only on the restored task MariaDB."""
import os,json,io
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db' and settings.DATABASES['default']['NAME']=='restore_check'
settings.SNP_UI_PREVIEW=True
settings.ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL=True
from django.core.management import call_command
from accounts.models import User,AccessAudit
from accounts.rbac import is_main
from accounts.preview_bootstrap import bootstrap_accounts
pk=int(os.environ['SNP_EXPECTED_ADMIN_PK'])
fields=['pk','username','password','email','name','phone_number','role','is_staff','is_superuser','is_active','account_state','rbac_managed','access_revision']
before=list(User.objects.order_by('pk').values(*fields));main_before={u.pk for u in User.objects.all() if is_main(u)}
call_command('migrate',interactive=False,verbosity=0)
call_command('rename_preview_admin',stdout=io.StringIO())
call_command('rename_preview_admin',apply=True,expected_pk=pk,stdout=io.StringIO())
# All required identities must already exist: no fallback secret or new user is allowed.
def unavailable_secret(name):raise AssertionError('Unexpected bootstrap secret request in restored fixture')
bootstrap_accounts(unavailable_secret)
after=list(User.objects.order_by('pk').values(*fields))
for row in after:
 if row['pk']==pk:assert row['username']=='admin';row['username']='verify-admin'
assert before==after
assert {u.pk for u in User.objects.all() if is_main(u)}==main_before
assert not User.objects.filter(username='verify-admin').exists()
assert AccessAudit.objects.filter(target_id=pk,action='account.username_changed').count()>=1
# Roll back username through the same atomic command, not by restoring/dropping live data.
call_command('rename_preview_admin',source='admin',target='verify-admin',apply=True,expected_pk=pk,stdout=io.StringIO())
assert before==list(User.objects.order_by('pk').values(*fields))
print(json.dumps({'passed':True,'restored_accounts':len(before),'same_pk_credentials_roles_and_flags':True,'seed_did_not_recreate_old_username':True,'rename_rollback_verified':True,'schema_migration_applied_without_account_drift':True,'real_preview_writes':False}))
