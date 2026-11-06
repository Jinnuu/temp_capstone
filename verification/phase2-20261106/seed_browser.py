"""Synthetic fixtures only in the task MariaDB schema; never Preview."""
import json
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
assert settings.DATABASES['default']['NAME']=='snp_auth_verification'
from accounts.models import User
from accounts.access_service import set_roles
from procurement.models import Supplier,SupplierMembership,PurchaseOrder,OrderItem,SupplierFulfillment
from inventory.models import Ingredient,SupplySpecification
from django.utils import timezone
assert not User.objects.filter(username__startswith='phase2-browser-').exists()
for suffix,role in [('buyer','DIETITIAN'),('a','SUPPLIER'),('b','SUPPLIER')]:
    u=User.objects.create_user('phase2-browser-'+suffix,password='isolated-browser-only',name='합성 '+suffix,
        role='SUPPLIER' if role=='SUPPLIER' else 'NUTRITIONIST',rbac_managed=True,account_state='ACTIVE',is_active=True)
    set_roles(u,{role})
    if role=='SUPPLIER':
        supplier=Supplier.objects.create(user=u,name='합성 공급업체 '+suffix,category='농산물')
        SupplierMembership.objects.create(account=u,supplier=supplier,status='VERIFIED')
        if suffix=='a':vendor=u
item=Ingredient.objects.create(name='분할 납품 검증 감자',unit='kg',safe_stock_level=0,supplier=vendor)
SupplySpecification.objects.create(ingredient=item,supplier=vendor,label='5kg/통',base_quantity=5,base_unit='kg',order_unit='통',unit_price=5000)
order=PurchaseOrder.objects.create(supplier=vendor,status='승인',total_amount=100000)
line=OrderItem.objects.create(purchase_order=order,ingredient=item,required_qty=100,missing_qty=100,
    order_unit_price=5000,estimated_price=100000,package_quantity=20,order_unit='통',spec_snapshot='5kg/통',target_date=timezone.localdate())
SupplierFulfillment.objects.create(order=order,state='ACCEPTED')
print(json.dumps({'order':order.pk,'item':line.pk,'ingredient':item.pk}))
