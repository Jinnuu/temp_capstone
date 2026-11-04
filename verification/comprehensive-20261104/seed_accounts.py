import os
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from django.contrib.auth import get_user_model
U=get_user_model();assert not U.objects.exists()
U.objects.create_superuser(username='verify-admin',password='isolated-browser-only',name='검증 관리자',role='ADMIN')
U.objects.create_user(username='verify-nutritionist',password='isolated-browser-only',name='검증 영양사')
U.objects.create_user(username='verify-supplier',password='isolated-browser-only',name='검증 공급업체',role='SUPPLIER')
print('Task-only account fixtures ready. No business records seeded.')
