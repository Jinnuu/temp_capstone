"""Regression contracts for the second team integration (isolated databases only)."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from inventory.models import Ingredient, InventoryLog, SupplySpecification
from meals.models import DietPlan, DietMenu, Menu, Recipe, CookingInstruction
from procurement.models import Supplier, PurchaseOrder, OrderItem
from procurement.workflow import save_headcount
from procurement.utils import calculate_physical_units


class KanghoonSecondIntegration(TestCase):
    def setUp(self):
        User=get_user_model()
        self.admin=User.objects.create_user(username='team2-admin',name='관리자',role='ADMIN',is_staff=True)
        self.operator=User.objects.create_user(username='team2-operator',name='영양사')
        self.vendor=User.objects.create_user(username='team2-vendor',name='기존업체',role='SUPPLIER')
        self.ing=Ingredient.objects.create(name='검증쌀',category='양곡/곡분가공품',unit='kg',unit_price=100,safe_stock_level=0,supplier=self.vendor)
        self.spec=SupplySpecification.objects.create(ingredient=self.ing,supplier=self.vendor,label='5kg/통',base_quantity=5,base_unit='kg',order_unit='통',unit_price=500)
        self.plan=DietPlan.objects.create(target_date=date(2026,11,6),meal_type='석식',headcount=999)
        self.menu=Menu.objects.create(name='검증식단')
        Recipe.objects.create(menu=self.menu,ingredient=self.ing,required_amount=100,unit='g')
        DietMenu.objects.create(diet_plan=self.plan,menu=self.menu)
        self.client.force_login(self.admin)

    def profile(self, **values):
        data={'name':'연동업체','category':'곡류','phone_number':'02-1234','user':str(self.vendor.pk)}
        data.update(values)
        return self.client.post(reverse('procurement:supplier_create'),data)

    def item(self, quantity=10, amount=1000, target=date(2026,11,6), ingredient=None):
        order=PurchaseOrder.objects.create(supplier=self.vendor,status='승인',total_amount=amount)
        return OrderItem.objects.create(purchase_order=order,ingredient=ingredient or self.ing,target_date=target,
            required_qty=quantity,missing_qty=quantity,order_unit_price=100,estimated_price=amount)

    def test_supplier_get_does_not_seed_accounts_or_profiles(self):
        before=get_user_model().objects.count()
        self.assertEqual(self.client.get(reverse('procurement:supplier_list')).status_code,200)
        self.assertEqual(Supplier.objects.count(),0)
        self.assertEqual(get_user_model().objects.count(),before)

    def test_supplier_links_existing_account_without_replacing_orders(self):
        item=self.item();self.assertEqual(self.profile().status_code,302)
        profile=Supplier.objects.get();self.assertEqual(profile.user_id,self.vendor.pk)
        self.vendor.refresh_from_db();self.assertEqual(self.vendor.role,'SUPPLIER')
        item.refresh_from_db();self.assertEqual(item.purchase_order.supplier_id,profile.user_id)

    def test_new_supplier_is_not_a_nutritionist_and_cannot_login(self):
        self.assertEqual(self.profile(user='',name='새업체').status_code,302)
        user=Supplier.objects.get().user
        self.assertEqual(user.role,'SUPPLIER');self.assertFalse(user.has_usable_password())

    def test_supplier_account_collision_and_invalid_input_are_rejected(self):
        self.profile()
        self.assertEqual(self.profile(name='두번째업체').status_code,400)
        self.assertEqual(self.profile(user='',name='').status_code,400)
        self.assertEqual(self.profile(user='',name='가'*51).status_code,400)
        self.assertEqual(Supplier.objects.count(),1)

    def test_non_supplier_account_cannot_be_linked(self):
        self.assertEqual(self.profile(user=str(self.admin.pk)).status_code,400)
        self.assertEqual(Supplier.objects.count(),0)

    def test_profile_update_keeps_identity_and_delete_retains_history(self):
        item=self.item();self.profile();profile=Supplier.objects.get()
        url=reverse('procurement:supplier_update',args=[profile.pk])
        self.assertEqual(self.client.post(url,{'category':'곡류','name':'수정업체','user':self.vendor.pk}).status_code,302)
        self.vendor.refresh_from_db();self.assertEqual(self.vendor.name,'수정업체')
        self.assertEqual(self.client.get(reverse('procurement:supplier_delete',args=[profile.pk])).status_code,405)
        self.assertEqual(self.client.post(reverse('procurement:supplier_delete',args=[profile.pk])).status_code,302)
        self.assertTrue(get_user_model().objects.filter(pk=self.vendor.pk).exists())
        self.assertTrue(OrderItem.objects.filter(pk=item.pk).exists())
        self.assertEqual(self.ing.supplier_id,self.vendor.pk)

    def test_supplier_mutations_require_admin_and_internal_documents_require_login(self):
        for user in [self.operator,self.vendor,None]:
            if user:self.client.force_login(user)
            else:self.client.logout()
            response=self.profile()
            self.assertIn(response.status_code,[302,403])
            for name in ['supplier_list','doc_cooking_instruction','doc_monthly_settlement']:
                response=self.client.get(reverse('procurement:'+name))
                self.assertEqual(response.status_code,200 if user==self.operator else (403 if user else 302))
        self.assertFalse(Supplier.objects.exists())

    def test_empty_month_has_real_zero_not_template_samples(self):
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-11'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['grand_total_amount'],0)
        self.assertNotContains(response,'CJ프레시웨이');self.assertNotContains(response,'3,795,000')
        self.assertContains(response,'조회 기간의 발주 내역이 없습니다.')
        self.assertContains(response,'세금 기준 미등록')

    def test_month_selection_prefers_target_date_and_only_falls_back_for_null(self):
        self.item(amount=1000)
        self.item(amount=9000,target=date(2026,10,6))
        self.item(amount=2000,target=None)
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-11'})
        # Null target uses the (test's actual) creation month, without OR-leaking explicit October orders.
        expected=3000 if timezone.localdate().strftime('%Y-%m')=='2026-11' else 1000
        self.assertEqual(response.context['grand_total_amount'],expected)

    def test_monthly_quantities_keep_units_and_zero_price(self):
        self.item(quantity=5,amount=0)
        other=Ingredient.objects.create(name='검증과일',unit='EA',unit_price=100,safe_stock_level=0,supplier=self.vendor)
        self.item(quantity=2,amount=200,ingredient=other)
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-11'})
        self.assertEqual(response.context['grand_total_amount'],200)
        self.assertEqual(response.context['grand_total_qty'],'2 EA / 5 kg')
        self.assertEqual(next(row['amount'] for row in response.context['item_details'] if row['ingredient_name']==self.ing.name),0)

    def test_month_invalid_and_cooking_range_invalid(self):
        self.assertEqual(self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'invalid'}).status_code,400)
        self.assertEqual(self.client.get(reverse('procurement:doc_cooking_instruction'),{'start_date':'2026-11-06','end_date':'2026-01-01'}).status_code,400)

    def test_team_cooking_uses_final_count_saved_notes_without_stock_changes(self):
        save_headcount(self.plan.pk,999,350)
        CookingInstruction.objects.create(diet_plan=self.plan,instructions='가열 확인',inventory_instructions='재고 확인',line_notes={str(self.menu.recipes.get().pk):'별도 배식'})
        response=self.client.get(reverse('procurement:doc_cooking_instruction'),{'date':'2026-11-06'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['diet_plans'][0]['headcount'],350)
        self.assertContains(response,'35 kg');self.assertContains(response,'7 통 사용분')
        self.assertContains(response,'별도 배식');self.assertContains(response,'가열 확인')
        self.assertFalse(InventoryLog.objects.exists())

    def test_team_cooking_zero_unconfirmed_and_missing_spec(self):
        url=reverse('procurement:doc_cooking_instruction')
        response=self.client.get(url,{'date':'2026-11-06'})
        self.assertEqual(response.context['diet_plans'][0]['headcount'],'미확정')
        self.assertContains(response,'미확정');self.assertNotContains(response,'500')
        save_headcount(self.plan.pk,0,0);self.spec.delete()
        response=self.client.get(url,{'date':'2026-11-06'})
        self.assertEqual(response.context['diet_plans'][0]['headcount'],0)
        self.assertContains(response,'0 kg');self.assertContains(response,'명시적 납품규격이 없습니다')

    def test_no_free_text_package_or_volume_mass_guessing(self):
        self.assertEqual(calculate_physical_units('5kg',35,'kg'),'35 kg')
        self.assertEqual(calculate_physical_units('5kg/통',35,'kg',specification=self.spec),'7 통')
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):calculate_physical_units('1L',35,'ml',specification=self.spec)

    def test_inventory_period_and_legacy_month_preserve_opening_balance(self):
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=10,
            transaction_date=timezone.make_aware(datetime(2026,10,1)))
        url=reverse('inventory:doc_inventory_status')
        for query in [{'month':'2026-11'},{'start_date':'2026-11-01','end_date':'2026-11-07'}]:
            response=self.client.get(url,query)
            self.assertEqual(response.status_code,200)
            self.assertEqual(len(response.context['inventory_list']),1)
        response=self.client.get(url,{'month':'2026-11','activity_only':'1'})
        self.assertEqual(len(response.context['inventory_list']),0)

    def test_existing_menu_name_creation_api_is_preserved(self):
        import json
        response=self.client.post(reverse('meals:add_diet_menu_api'),
            data=json.dumps({'date':str(self.plan.target_date),'meal_type':'석식','menu_name':'신규검증메뉴'}),
            content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertTrue(Menu.objects.filter(name='신규검증메뉴').exists())

    def test_prediction_retry_only_runs_missing_meals(self):
        from forecasting.models import AttendancePrediction
        # Inspect the actual route and use a mocked inference boundary: no model replacement.
        AttendancePrediction.objects.create(prediction_date=self.plan.target_date,meal_type='breakfast',predicted_count=10)
        with patch('forecasting.views.run_attendance_prediction') as run:
            response=self.client.post(reverse('forecasting:prediction_create'),{'prediction_date':str(self.plan.target_date)})
        self.assertIn(response.status_code,[200,302])
        self.assertEqual(run.call_count,2)

    def test_completed_prediction_retry_never_reruns_models(self):
        from forecasting.models import AttendancePrediction
        for meal in ['breakfast','lunch','dinner']:
            AttendancePrediction.objects.create(prediction_date=self.plan.target_date,meal_type=meal,predicted_count=10)
        with patch('forecasting.views.run_attendance_prediction') as run:
            response=self.client.post(reverse('forecasting:prediction_create'),{'prediction_date':str(self.plan.target_date)})
        self.assertEqual(run.call_count,0)
        self.assertEqual(response.status_code,302)

    def test_prediction_calendar_exposes_each_meal_count(self):
        from forecasting.models import AttendancePrediction
        for meal,count in [('breakfast',10),('lunch',20),('dinner',30)]:
            AttendancePrediction.objects.create(prediction_date=self.plan.target_date,meal_type=meal,predicted_count=count)
        response=self.client.get(reverse('forecasting:prediction_calendar'),{'year':2026,'month':11})
        self.assertEqual(response.status_code,200)
        row=next(day for week in response.context['calendar_weeks'] for day in week if day and day['date']==self.plan.target_date)
        self.assertEqual(row['total_count'],60)
        self.assertEqual(len(row['predictions']),3)

    def ingredient_edit(self, **changes):
        data={'category':self.ing.category,'name':self.ing.name,'supplier':self.vendor.pk,
              'spec':'5kg/통','unit':'kg','unit_price':200,'safe_stock_level':'0'}
        data.update(changes)
        return self.client.post(reverse('inventory:ingredient_update',args=[self.ing.pk]),data)

    def test_ingredient_edit_keeps_primary_key_and_inventory(self):
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=10)
        response=self.ingredient_edit(name='수정검증쌀')
        self.assertEqual(response.status_code,302)
        self.ing.refresh_from_db();self.assertEqual((self.ing.name,self.ing.unit_price),('수정검증쌀',200))
        self.assertEqual(InventoryLog.objects.get().quantity,10)
        self.assertEqual(self.menu.recipes.get().ingredient_id,self.ing.pk)

    def test_ingredient_edit_cannot_reinterpret_existing_units(self):
        response=self.ingredient_edit(unit='g')
        self.assertContains(response,'기준 단위는 직접 변경할 수 없습니다')
        self.ing.refresh_from_db();self.assertEqual(self.ing.unit,'kg')

    def test_ingredient_edit_rejects_negative_price(self):
        response=self.ingredient_edit(unit_price=-1)
        self.assertIn('unit_price',response.context['form'].errors)
        self.ing.refresh_from_db();self.assertEqual(self.ing.unit_price,100)
