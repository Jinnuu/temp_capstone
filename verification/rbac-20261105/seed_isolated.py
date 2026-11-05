import django
from django.conf import settings
django.setup()
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from accounts.models import User
from accounts.access_service import set_roles
assert not User.objects.exists()
for name,role,app_roles in [('verify-admin','ADMIN',{'SYSTEM_ADMIN'}),('verify-nutritionist','NUTRITIONIST',{'DIETITIAN'}),('verify-supplier','SUPPLIER',set()),('rbac-viewer','NUTRITIONIST',{'VIEWER'}),('rbac-cook','NUTRITIONIST',{'COOK'})]:
    user=User.objects.create_user(name,name=name,email=name+'@example.invalid',password='isolated-browser-only',role=role,is_active=True,rbac_managed=True,account_state='ACTIVE',is_staff=name=='verify-admin',is_superuser=name=='verify-admin')
    set_roles(user,app_roles)
print('Five synthetic accounts created in empty task-only SQLite.')
