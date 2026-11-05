"""Only the current task's tmpfs SQLite may receive this synthetic fixture."""
import os
import django
django.setup()
from django.conf import settings
assert os.environ.get('SNP_HARDENING_BROWSER') == '1'
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME'] == '/tmp/sprint7-integration.sqlite3'
from accounts.models import User
from accounts.access_service import set_roles
from procurement.models import Supplier
from meals.models import DietPlan,DietMenu,Menu
from datetime import date
u=User.objects.create_user('hardening-admin-vendor',name='보호 관리자 업체',role='SUPPLIER',is_active=True,rbac_managed=True,account_state='ACTIVE')
set_roles(u,{'SUPPLIER','SUB_ADMIN'})
s=Supplier.objects.create(user=u,name='보호 관리자 업체',category='농산물')
m=Menu.objects.create(name='보존 식단 메뉴')
p=DietPlan.objects.create(target_date=date(2026,11,4),meal_type='중식',headcount=120,final_headcount=100,is_served=True)
DietMenu.objects.create(diet_plan=p,menu=m)
import json
print(json.dumps({'protected_user':u.pk,'protected_profile':s.pk,'served_plan':p.pk}))
