"""Migrate a restored snapshot in task-only MariaDB, never the Preview DB."""
import os, json, hashlib
os.environ['DJANGO_SETTINGS_MODULE']='config.auth_mysql_test_settings'
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
settings.DATABASES['default']['NAME']='restore_check'
import django
django.setup()
from django.db import connection
from django.core.management import call_command
fields='id, username, password, email, role, is_active, is_staff, is_superuser'
with connection.cursor() as c:
    c.execute('SELECT '+fields+' FROM accounts_user ORDER BY id');before=c.fetchall()
call_command('migrate',verbosity=0,interactive=False)
with connection.cursor() as c:
    c.execute('SELECT '+fields+' FROM accounts_user ORDER BY id');after=c.fetchall()
assert before==after
from accounts.models import User
from accounts.rbac import roles
assert User.objects.filter(is_active=False).exclude(account_state='LEGACY_INACTIVE').count()==0
assert User.objects.filter(is_active=True).exclude(account_state='ACTIVE').count()==0
assert User.objects.filter(rbac_managed=False).count()==0
print(json.dumps({'passed':True,'restoredAccounts':len(before),'credentialEmailLegacyRoleAndFlagsUnchanged':True,'allExistingInactiveRemainUnknown':True,'activeAdmins':sum('SYSTEM_ADMIN' in roles(u) for u in User.objects.filter(is_active=True))}))
