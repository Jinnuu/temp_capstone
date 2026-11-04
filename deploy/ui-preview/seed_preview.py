"""Idempotent synthetic account bootstrap for this new preview DB only."""
import os
from pathlib import Path
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.preview_settings')
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
if os.environ.get('SNP_UI_PREVIEW') != '1' or settings.DATABASES['default']['NAME'] != 'snp_ui_preview' or settings.DATABASES['default']['HOST'] != 'db':
    raise RuntimeError('Refusing to seed outside the isolated preview database')
password = Path('/run/secrets/demo_password').read_text().strip()
with transaction.atomic():
    for name, label, role, staff in [('verify-admin','시범 관리자','ADMIN',True),('verify-nutritionist','시범 영양사','NUTRITIONIST',False),('verify-supplier','시범 공급업체','SUPPLIER',False)]:
        user, created = get_user_model().objects.get_or_create(username=name, defaults={'name':label,'role':role,'is_staff':staff,'is_superuser':staff,'is_active':True})
        if created:
            user.set_password(password)
            user.save()
print('Preview accounts ready; existing users and business records preserved.')
