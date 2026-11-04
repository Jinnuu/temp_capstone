"""Only for the task-created tmpfs browser application; no business data seeding."""
import os
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from django.contrib.auth import get_user_model
User=get_user_model()
User.objects.create_user(username='readiness-admin',password='disposable-test-only',name='검증 관리자',is_staff=True,role='ADMIN')
User.objects.create_user(username='readiness-nutritionist',password='disposable-test-only',name='검증 영양사',role='NUTRITIONIST')
User.objects.create_user(username='readiness-supplier',password='disposable-test-only',name='검증 공급업체',role='SUPPLIER')
print('Readiness test accounts ready; business data must be created through UI')
