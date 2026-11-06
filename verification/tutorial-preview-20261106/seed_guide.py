"""Extra preapproved synthetic roles only on the task SQLite."""
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from accounts.models import User
from accounts.access_service import set_roles
for name,role in [('guide-second','DIETITIAN'),('guide-viewer','VIEWER'),('guide-cook','COOK')]:
    assert not User.objects.filter(username=name).exists()
    user=User.objects.create_user(name,name='합성 가이드 사용자',password='isolated-browser-only',role='NUTRITIONIST',is_active=True,rbac_managed=True,account_state='ACTIVE')
    set_roles(user,{role})
print('Synthetic guide roles created only on task SQLite.')
