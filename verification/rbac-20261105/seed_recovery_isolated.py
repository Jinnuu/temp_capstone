import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from accounts.models import User
from accounts.access_service import set_roles
for name,email,state in [('auth-active','owner@example.invalid','ACTIVE'),('auth-second','owner@example.invalid','ACTIVE'),('auth-pending','pending@example.invalid','PENDING')]:
    assert not User.objects.filter(username=name).exists()
    user=User.objects.create_user(name,email=email,name=name,password='Test-Only-Account-Password-981!',account_state=state,is_active=state=='ACTIVE',rbac_managed=True)
    set_roles(user,{'DIETITIAN'})
print('Synthetic recovery fixtures added only to task SQLite.')
