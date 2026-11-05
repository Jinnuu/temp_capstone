"""Fixture creation is restricted to task-only SQLite, never preview MariaDB."""
import django
from django.conf import settings
django.setup()
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from django.contrib.auth import get_user_model
U=get_user_model();assert not U.objects.exists()
for name,email,active in [('auth-active','owner@example.invalid',True),('auth-second','owner@example.invalid',True),('auth-pending','pending@example.invalid',False)]:
    U.objects.create_user(username=name,name=name,email=email,is_active=active,password='Test-Only-Account-Password-981!')
print('Synthetic isolated auth fixture ready.')
