"""Synthetic test accounts only, no sample meal/order/stock data."""
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
assert settings.DATABASES['default']['NAME']=='snp_auth_verification'
from accounts.models import User
from accounts.access_service import set_roles
assert not User.objects.filter(username__startswith='beginner-').exists()
for name,role in [('dietitian','DIETITIAN'),('second','DIETITIAN'),('viewer','VIEWER'),('cook','COOK'),('supplier','SUPPLIER')]:
    user=User.objects.create_user('beginner-'+name,name='합성 가이드 사용자',password='isolated-browser-only',
        role='SUPPLIER' if role=='SUPPLIER' else 'NUTRITIONIST',rbac_managed=True,account_state='ACTIVE',is_active=True)
    set_roles(user,{role})
print('Five synthetic test accounts; no meal, procurement, inspection or inventory fixtures created.')
