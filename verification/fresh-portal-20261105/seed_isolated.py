import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from accounts.models import User, Announcement
from accounts.access_service import set_roles
from procurement.models import Supplier, SupplierMembership, PurchaseOrder, OrderItem
from inventory.models import Ingredient
from django.utils import timezone
assert not User.objects.exists()
for name,role,assigned in [('verify-admin','ADMIN',{'MAIN_ADMIN'}),('verify-nutritionist','NUTRITIONIST',{'DIETITIAN'}),('verify-supplier','SUPPLIER',{'SUPPLIER'}),('fresh-sub','NUTRITIONIST',{'SUB_ADMIN'}),('fresh-supplier-a','SUPPLIER',{'SUPPLIER'}),('fresh-supplier-b','SUPPLIER',{'SUPPLIER'})]:
    u=User.objects.create_user(name,name=name,email=name+'@example.invalid',password='isolated-browser-only',role=role,is_active=True,rbac_managed=True,account_state='ACTIVE',is_staff=name=='verify-admin',is_superuser=name=='verify-admin')
    set_roles(u,assigned)
for suffix,name in [('a','시범 A 채소 유통'),('b','시범 B 과일 유통')]:
    u=User.objects.get(username='fresh-supplier-'+suffix)
    supplier=Supplier.objects.create(user=u,name=name,category='농산물')
    SupplierMembership.objects.create(account=u,supplier=supplier,requested_company=name,contact_name='시범 담당자',contact_phone='02-0000-0000',status='VERIFIED')
    ingredient=Ingredient.objects.create(name=name+' 신선 재료',unit='kg',safe_stock_level=0,unit_price=100,supplier=u)
    order=PurchaseOrder.objects.create(supplier=u,status='승인',total_amount=1000)
    OrderItem.objects.create(purchase_order=order,ingredient=ingredient,required_qty=10,missing_qty=10,order_unit_price=100,estimated_price=1000,target_date=timezone.localdate(),meal_type='',package_quantity=2,order_unit='봉',spec_snapshot='5kg/봉')
Announcement.objects.create(title='시범 데이터 안내',message='이 환경의 데이터는 격리된 합성 데이터입니다.',author=User.objects.get(username='verify-admin'))
print('Synthetic identity, company and order fixture created only in task SQLite.')
