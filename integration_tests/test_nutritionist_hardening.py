"""Audit regressions: real views/ORM, isolated test DB only."""
import io
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from accounts.access_service import set_roles
from accounts.models import AccessAudit
from forecasting.models import MealForecast, AttendancePrediction
from inventory.models import Ingredient
from meals.models import Menu, Recipe, DietPlan, DietMenu
from procurement.models import Supplier, PurchaseOrder, OrderItem, ProcurementPlan

User = get_user_model()

class NutritionistHardeningTests(TestCase):
    def setUp(self):
        self.main = User.objects.create_superuser('audit-main', 'main@example.invalid', 'isolated-test-password')
        self.sub = self.user('audit-sub', {'SUB_ADMIN'})
        self.vendor = self.user('audit-supplier', {'SUPPLIER'}, 'SUPPLIER')
        self.vendor_sub = self.user('audit-supplier-sub', {'SUPPLIER', 'SUB_ADMIN'}, 'SUPPLIER')
        self.profile = Supplier.objects.create(user=self.vendor, name='같은 이름', category='농산물')
        self.protected_profile = Supplier.objects.create(user=self.vendor_sub, name='같은 이름', category='농산물')
        self.ing = Ingredient.objects.create(name='감사 재료', unit='kg', safe_stock_level=0, unit_price=100, supplier=self.vendor)
        self.menu = Menu.objects.create(name='원래 메뉴')
        self.recipe = Recipe.objects.create(menu=self.menu, ingredient=self.ing, unit='g', required_amount=100)
        self.plan = DietPlan.objects.create(target_date=date(2026,11,6), meal_type='중식', headcount=120, final_headcount=100, is_confirmed=True)
        DietMenu.objects.create(diet_plan=self.plan, menu=self.menu)
        self.client.force_login(self.main)

    def user(self, name, roles, kind='NUTRITIONIST'):
        user = User.objects.create_user(name, role=kind, name=name, is_active=True, rbac_managed=True, account_state='ACTIVE')
        set_roles(user, roles)
        return user

    def upload(self, text):
        return self.client.post(reverse('meals:mealplan_bulk_upload'), {'mealplan_file':SimpleUploadedFile('plans.csv', text.encode('utf-8-sig'), content_type='text/csv')})

    def prediction(self, value=130):
        return AttendancePrediction.objects.create(prediction_date=self.plan.target_date, meal_type='lunch', predicted_count=value, model_name='audit-model')

    def report(self):
        return self.client.get(reverse('forecasting:weekly_forecast_report'), {'date':self.plan.target_date})

    def test_sub_cannot_edit_supplier_admin_through_legacy_form(self):
        self.client.force_login(self.sub)
        r = self.client.post(reverse('procurement:workflow_supplier_edit', args=[self.vendor_sub.pk]), {'username':'changed-admin','name':'변경','phone_number':''})
        self.assertEqual(r.status_code,403)
        self.vendor_sub.refresh_from_db();self.assertEqual(self.vendor_sub.username,'audit-supplier-sub')
        self.assertTrue(AccessAudit.objects.filter(actor=self.sub,target=self.vendor_sub,result='DENIED').exists())

    def test_sub_cannot_edit_own_supplier_admin(self):
        self.client.force_login(self.vendor_sub)
        r=self.client.post(reverse('procurement:workflow_supplier_edit',args=[self.vendor_sub.pk]),{'username':'changed-self','name':'변경','phone_number':''})
        self.assertEqual(r.status_code,403)

    def test_sub_cannot_edit_supplier_admin_via_profile(self):
        self.client.force_login(self.sub)
        r=self.client.post(reverse('procurement:supplier_update',args=[self.protected_profile.pk]),{'user':self.vendor_sub.pk,'name':'변경 업체','category':'농산물'})
        self.assertEqual(r.status_code,403)
        self.protected_profile.refresh_from_db();self.assertEqual(self.protected_profile.name,'같은 이름')
        self.assertTrue(AccessAudit.objects.filter(actor=self.sub,target=self.vendor_sub,result='DENIED').exists())

    def test_sub_cannot_delete_supplier_admin_profile(self):
        self.client.force_login(self.sub)
        self.assertEqual(self.client.post(reverse('procurement:supplier_delete',args=[self.protected_profile.pk])).status_code,403)
        self.assertTrue(Supplier.objects.filter(pk=self.protected_profile.pk).exists())

    def test_main_can_edit_supplier_admin_and_audit(self):
        r=self.client.post(reverse('procurement:workflow_supplier_edit',args=[self.vendor_sub.pk]),{'username':self.vendor_sub.username,'name':'정상 수정','phone_number':''})
        self.assertEqual(r.status_code,302)
        self.vendor_sub.refresh_from_db();self.assertEqual(self.vendor_sub.name,'정상 수정')
        self.assertTrue(AccessAudit.objects.filter(actor=self.main,target=self.vendor_sub,result='SUCCESS',action__startswith='supplier.').exists())

    def test_sub_can_edit_general_supplier_and_audit(self):
        self.client.force_login(self.sub)
        r=self.client.post(reverse('procurement:workflow_supplier_edit',args=[self.vendor.pk]),{'username':self.vendor.username,'name':'일반 수정','phone_number':''})
        self.assertEqual(r.status_code,302)
        self.assertTrue(AccessAudit.objects.filter(actor=self.sub,target=self.vendor,result='SUCCESS',action__startswith='supplier.').exists())

    def test_general_supplier_cannot_edit_another_company(self):
        self.client.force_login(self.vendor)
        self.assertEqual(self.client.post(reverse('procurement:workflow_supplier_edit',args=[self.vendor_sub.pk]),{}).status_code,403)

    def test_missing_actual_is_not_manual_or_final(self):
        self.prediction()
        response=self.report();row=response.context['report_items'][0]
        self.assertIsNone(row['actual_count']);self.assertIsNone(row['error_rate'])
        self.assertEqual((row['manual_count'],row['final_count']),(120,100))
        self.assertContains(response,'미입력');self.assertContains(response,'산출 불가')

    def test_actual_zero_is_not_missing_and_percentage_undefined(self):
        self.prediction();MealForecast.objects.create(diet_plan=self.plan,predicted_count=130,actual_count=0)
        row=self.report().context['report_items'][0]
        self.assertEqual(row['actual_count'],0);self.assertIsNone(row['error_rate'])

    def test_positive_actual_percentage_uses_measured_value(self):
        self.prediction();MealForecast.objects.create(diet_plan=self.plan,predicted_count=10,actual_count=125)
        row=self.report().context['report_items'][0]
        self.assertEqual(row['actual_count'],125);self.assertAlmostEqual(float(row['error_rate']),4)

    def test_missing_prediction_is_not_zero(self):
        MealForecast.objects.create(diet_plan=self.plan,predicted_count=10,actual_count=125)
        row=self.report().context['report_items'][0]
        self.assertIsNone(row['predicted_count']);self.assertIsNone(row['error_rate'])

    def test_excel_shares_measured_semantics(self):
        self.prediction()
        r=self.client.get(reverse('forecasting:export_weekly_forecast_excel'),{'date':self.plan.target_date})
        rows=list(load_workbook(io.BytesIO(r.content)).active.values)
        self.assertEqual(rows[0][4:],('AI 예측 식수','수동 예상 식수','최종 확정 식수','실제 식수','예측 오차율(%)'))
        self.assertEqual(rows[1][4:],(130,120,100,'미입력','산출 불가'))

    def test_served_upload_is_rejected_and_original_preserved(self):
        self.plan.is_served=True;self.plan.save()
        self.upload('날짜,끼니,메뉴명,식수\n2026-11-06,중식,교체 메뉴,999\n')
        self.plan.refresh_from_db()
        self.assertEqual((self.plan.headcount,self.plan.final_headcount),(120,100))
        self.assertEqual(list(self.plan.diet_menus.values_list('menu__name',flat=True)),['원래 메뉴'])

    def test_bulk_upload_is_atomic_when_later_plan_is_served(self):
        self.plan.is_served=True;self.plan.save()
        self.upload('날짜,끼니,메뉴명,식수\n2026-11-05,중식,추가 메뉴,1\n2026-11-06,중식,교체 메뉴,999\n')
        self.assertFalse(DietPlan.objects.filter(target_date=date(2026,11,5)).exists())
        self.assertFalse(Menu.objects.filter(name='추가 메뉴').exists())

    def test_upload_marks_existing_orders_for_review(self):
        plan=ProcurementPlan.objects.create(start_date=self.plan.target_date,end_date=self.plan.target_date,meal_ids=[self.plan.pk],source_fingerprint='old')
        order=PurchaseOrder.objects.create(supplier=self.vendor,workflow_plan=plan)
        self.upload('날짜,끼니,메뉴명,식수\n2026-11-06,중식,변경 메뉴,110\n')
        plan.refresh_from_db();order.refresh_from_db()
        self.assertTrue(plan.needs_review);self.assertTrue(order.needs_review)

    def test_recipe_change_used_by_served_plan_is_blocked(self):
        self.plan.is_served=True;self.plan.save()
        from meals.views import save_recipe_rows
        with self.assertRaises(ValidationError):save_recipe_rows(self.menu,[self.ing.pk],['200'],units=['g'])
        self.recipe.refresh_from_db();self.assertEqual(self.recipe.required_amount,100)

    def test_order_detail_does_not_invent_tax(self):
        order=PurchaseOrder.objects.create(supplier=self.vendor,total_amount=1000)
        OrderItem.objects.create(purchase_order=order,ingredient=self.ing,required_qty=10,missing_qty=10,order_unit_price=100,estimated_price=1000)
        response=self.client.get(reverse('procurement:order_detail',args=[order.pk]))
        self.assertIsNone(response.context['vat']);self.assertIsNone(response.context['total'])
        self.assertContains(response,'세금 기준 미등록');self.assertNotContains(response,'부가가치세 (10%)')

    def test_monthly_same_name_suppliers_remain_separate(self):
        for vendor in [self.vendor,self.vendor_sub]:
            order=PurchaseOrder.objects.create(supplier=vendor,total_amount=1000)
            OrderItem.objects.create(purchase_order=order,ingredient=self.ing,required_qty=10,missing_qty=10,order_unit_price=100,estimated_price=1000,target_date=self.plan.target_date)
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-11'})
        self.assertEqual(len(response.context['supplier_summary']),2)
        self.assertEqual({row['supplier_id'] for row in response.context['supplier_summary']},{self.vendor.pk,self.vendor_sub.pk})

    def test_report_json_uses_same_four_counts(self):
        self.prediction()
        response=self.client.get(reverse('forecasting:weekly_forecast_report'),{'date':self.plan.target_date,'format':'json'})
        row=response.json()['report_items'][0]
        self.assertEqual((row['predicted_count'],row['manual_count'],row['final_count'],row['actual_count']),(130,120,100,None))
        self.assertIsNone(row['error_rate'])

    def test_latest_prediction_is_selected_consistently(self):
        self.prediction(130);self.prediction(140)
        self.assertEqual(self.report().context['report_items'][0]['predicted_count'],140)

    def test_negative_legacy_actual_is_not_accuracy_evidence(self):
        self.prediction();MealForecast.objects.create(diet_plan=self.plan,predicted_count=130,actual_count=-1)
        row=self.report().context['report_items'][0]
        self.assertIsNone(row['actual_count']);self.assertIsNone(row['error_rate']);self.assertTrue(row['invalid_actual'])

    def test_ajax_change_marks_plan_for_review(self):
        snapshot=ProcurementPlan.objects.create(start_date=self.plan.target_date,end_date=self.plan.target_date,meal_ids=[self.plan.pk],source_fingerprint='old')
        new=Menu.objects.create(name='추가 메뉴')
        r=self.client.post(reverse('meals:add_diet_menu_api'),{'date':str(self.plan.target_date),'meal_type':'중식','menu_id':new.pk},content_type='application/json')
        self.assertEqual(r.status_code,200);snapshot.refresh_from_db();self.assertTrue(snapshot.needs_review)

    def test_snapshot_referenced_plan_cannot_be_bulk_deleted(self):
        snapshot=ProcurementPlan.objects.create(start_date=self.plan.target_date,end_date=self.plan.target_date,meal_ids=[self.plan.pk],source_fingerprint='old')
        self.client.post(reverse('meals:bulk_delete_mealplans'),{'start_date':str(self.plan.target_date),'end_date':str(self.plan.target_date)})
        self.assertTrue(DietPlan.objects.filter(pk=self.plan.pk).exists())
        self.assertTrue(ProcurementPlan.objects.filter(pk=snapshot.pk).exists())

    def test_public_approval_opt_in_preserves_existing_accounts(self):
        from django.test import override_settings
        from accounts.access_service import register
        with override_settings(ACCOUNT_APPROVAL_MODE='auto', ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL=True):
            new=User(username='pending-public',name='대기 영양사',role='NUTRITIONIST')
            register(new,'DIETITIAN')
        self.assertFalse(new.is_active);self.assertEqual(new.account_state,'PENDING')
        self.main.refresh_from_db();self.assertTrue(self.main.is_active)

    def test_public_supplier_waits_when_approval_opted_in(self):
        from django.test import override_settings
        from accounts.access_service import register
        with override_settings(ACCOUNT_APPROVAL_MODE='auto', ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL=True):
            new=User(username='pending-vendor',name='대기 공급업체',role='SUPPLIER')
            register(new,'SUPPLIER')
        self.assertFalse(new.is_active)

    def test_money_preserves_fractional_accepted_value_and_unknown_tax(self):
        from procurement.money import accepted_amount, review_totals
        order=PurchaseOrder.objects.create(supplier=self.vendor,total_amount=1000)
        item=OrderItem.objects.create(purchase_order=order,ingredient=self.ing,required_qty=3,missing_qty=3,order_unit_price=100,estimated_price=1000)
        self.assertEqual(accepted_amount(item,Decimal('1.5')),Decimal('500'))
        total=review_totals([item]);self.assertEqual(total['recorded_total'],1000)
        self.assertIsNone(total['tax_amount']);self.assertIsNone(total['payable_amount'])

    def test_money_rejects_invalid_snapshot_without_silent_zero(self):
        from procurement.money import recorded_amount
        from types import SimpleNamespace
        for value in ('NaN','Infinity','-1'):
            with self.subTest(value=value),self.assertRaises(ValidationError):recorded_amount(SimpleNamespace(estimated_price=value))

    def test_sub_cannot_edit_supplier_main_through_legacy_routes(self):
        set_roles(self.vendor_sub, {'MAIN_ADMIN','SUPPLIER'})
        self.client.force_login(self.sub)
        for name,pk,data in [
            ('procurement:workflow_supplier_edit',self.vendor_sub.pk,{'username':self.vendor_sub.username,'name':'차단','phone_number':''}),
            ('procurement:supplier_update',self.protected_profile.pk,{'user':self.vendor_sub.pk,'name':'차단','category':'농산물'}),
        ]:
            with self.subTest(route=name):self.assertEqual(self.client.post(reverse(name,args=[pk]),data).status_code,403)

    def test_profile_creation_cannot_attach_protected_admin(self):
        self.protected_profile.delete()
        self.client.force_login(self.sub)
        self.assertEqual(self.client.post(reverse('procurement:supplier_create'),{'user':self.vendor_sub.pk,'name':'차단','category':'농산물'}).status_code,403)
        self.assertFalse(Supplier.objects.filter(user=self.vendor_sub).exists())

    def test_native_admin_does_not_allow_served_menu_edit(self):
        self.plan.is_served=True;self.plan.save()
        self.assertEqual(self.client.get(reverse('admin:meals_menu_change',args=[self.menu.pk])).status_code,403)

    def test_recipe_upload_rolls_back_when_any_menu_was_served(self):
        from openpyxl import Workbook
        self.plan.is_served=True;self.plan.save()
        wb=Workbook();ws=wb.active
        ws.append(['메뉴명','식재료명','사용량','단위'])
        ws.append(['새로운 메뉴','감사 재료',200,'g'])
        ws.append(['원래 메뉴','감사 재료',200,'g'])
        stream=io.BytesIO();wb.save(stream)
        r=self.client.post(reverse('meals:recipe_upload_api'),{'excel_file':SimpleUploadedFile('recipe.xlsx',stream.getvalue())})
        self.assertEqual(r.status_code,409)
        self.assertFalse(Menu.objects.filter(name='새로운 메뉴').exists())
        self.recipe.refresh_from_db();self.assertEqual(self.recipe.required_amount,100)

    def test_legacy_recipe_form_does_not_delete_served_recipe(self):
        self.plan.is_served=True;self.plan.save()
        r=self.client.post(reverse('meals:recipe_create'),{'menu_id':self.menu.pk,'ingredient_id[]':[self.ing.pk],'required_amount[]':['200'],'recipe_unit[]':['g']})
        self.assertEqual(r.status_code,400)
        self.recipe.refresh_from_db();self.assertEqual(self.recipe.required_amount,100)

    def test_supplier_does_not_have_empty_internal_navigation_groups(self):
        self.client.force_login(self.vendor)
        r=self.client.get(reverse('procurement:portal_home'))
        self.assertNotContains(r,'01</span> 식단·레시피')
        self.assertNotContains(r,'02</span> 식수·소요량')
        self.assertContains(r,'공급업체 업무')

    def test_empty_month_has_zero_items_not_example_twelve(self):
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-01'})
        self.assertTrue('총 품목 수: <span class="val">0</span>' in response.content.decode(), 'Empty month must show zero items; response body omitted to protect CSRF token')

    def test_linked_profile_delete_failure_is_audited_without_deleting(self):
        from procurement.models import SupplierMembership
        SupplierMembership.objects.create(account=self.vendor,supplier=self.profile,requested_company='합성 업체',contact_name='합성 담당',contact_phone='000',status='VERIFIED')
        r=self.client.post(reverse('procurement:supplier_delete',args=[self.profile.pk]))
        self.assertEqual(r.status_code,302)
        self.assertTrue(Supplier.objects.filter(pk=self.profile.pk).exists())
        self.assertTrue(AccessAudit.objects.filter(actor=self.main,target=self.vendor,result='DENIED',action='supplier.delete_denied').exists())

    def test_money_keeps_documented_overdelivery_supported_by_inspection(self):
        # Existing inspect_item explicitly allows quantity differences with a reason.
        # A read-only reporting helper must not impose a new upper-bound policy.
        from procurement.money import accepted_amount
        from procurement.workflow import inspect_item
        order=PurchaseOrder.objects.create(supplier=self.vendor,total_amount=1000,status='승인')
        item=OrderItem.objects.create(purchase_order=order,ingredient=self.ing,required_qty=3,missing_qty=3,order_unit_price=100,estimated_price=1000)
        inspection=inspect_item(item.pk,self.main,delivered=4,accepted=4,condition='정상',specification='명시 규격',notes='발주량 초과 납품을 구매자가 확인한 합성 시험')
        self.assertEqual(inspection.accepted_qty,4)
        self.assertEqual(accepted_amount(item,inspection.accepted_qty),Decimal('4000')/Decimal('3'))
        from django.utils import timezone
        response=self.client.get(reverse('procurement:workflow_settlement'),{'month':timezone.localdate().strftime('%Y-%m')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['rows'][0]['inspected_amount'],Decimal('4000')/Decimal('3'))
