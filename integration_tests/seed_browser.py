"""Only run against config.test_settings and its ephemeral SQLite database."""
import os
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from django.contrib.auth import get_user_model
from inventory.models import Ingredient,SupplySpecification
from meals.models import DietPlan,DietMenu,Menu,Recipe
from datetime import date
User=get_user_model()
operator=User.objects.create_user(username='browser-nutritionist',password='browser-test-only',name='검증 영양사',is_staff=True)
vendor=User.objects.create_user(username='browser-vendor',name='가나다 식품',role='SUPPLIER')
ing=Ingredient.objects.create(name='브라우저 참치',unit='kg',safe_stock_level=0,unit_price=100,supplier=vendor,category='통조림')
SupplySpecification.objects.create(ingredient=ing,supplier=vendor,label='5kg / 캔',base_quantity=5,base_unit='kg',order_unit='캔',unit_price=500)
menu=Menu.objects.create(name='브라우저 참치볶음')
Recipe.objects.create(menu=menu,ingredient=ing,required_amount=100,unit='g')
plan=DietPlan.objects.create(target_date=date(2026,10,16),meal_type='석식',headcount=100)
DietMenu.objects.create(diet_plan=plan,menu=menu)
print('Isolated browser fixtures ready')
