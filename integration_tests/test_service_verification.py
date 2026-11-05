"""Adversarial service and cross-document regression scenarios, isolated DB only."""
import io,json,uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch
import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase,Client
from django.urls import reverse
from django.utils import timezone
from inventory.models import Ingredient,SupplySpecification,InventoryLog
from meals.models import Menu,Recipe,DietPlan,DietMenu
from procurement.models import OrderItem,PurchaseOrder
from procurement.workflow import save_headcount,create_plan,confirm_orders,create_manual_plan


class ServiceVerification(TestCase):
    def setUp(self):
        U=get_user_model()
        self.user=U.objects.create_user(username='verify-admin',name='검증 관리자',is_staff=True,role='ADMIN')
        self.vendor=U.objects.create_user(username='verify-supplier',name='검증 업체',role='SUPPLIER')
        self.client.force_login(self.user)
        self.ing=Ingredient.objects.create(name='검증 재료',unit='kg',unit_price=123,safe_stock_level=0,supplier=self.vendor,category='기타식품')
        self.spec=SupplySpecification.objects.create(ingredient=self.ing,supplier=self.vendor,label='5kg/통',base_quantity=5,base_unit='kg',order_unit='통',unit_price=500)
        self.menu=Menu.objects.create(name='검증 메뉴',category='기타')
        self.recipe=Recipe.objects.create(menu=self.menu,ingredient=self.ing,required_amount=100,unit='g')
        self.plan=DietPlan.objects.create(target_date=date(2026,11,6),meal_type='석식',headcount=999)
        self.link=DietMenu.objects.create(diet_plan=self.plan,menu=self.menu)

    def issue(self):
        save_headcount(self.plan.pk,999,351)
        plan=create_plan(self.plan.target_date,self.plan.target_date,self.user,uuid.uuid4())
        orders=confirm_orders(plan.pk,self.user,{str(plan.lines.get().pk):9})
        return plan,orders[0].items.get()

    def post_json(self,name,data,**kw):
        return self.client.post(reverse('meals:'+name),json.dumps(data),content_type='application/json',**kw)

    def test_csrf_all_three_menu_mutations_reject_missing_token(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        for name,args,data in [('add_diet_menu_api',[],{'date':'2026-11-06','meal_type':'석식','menu_name':'추가'}),
                              ('remove_diet_menu_api',[],{'date':'2026-11-06','meal_type':'석식','menu_id':self.menu.pk}),
                              ('delete_diet_menu_api',[self.link.pk],{})]:
            with self.subTest(name=name):
                response=client.post(reverse('meals:'+name,args=args),json.dumps(data),content_type='application/json')
                self.assertEqual(response.status_code,403)
        self.assertTrue(DietMenu.objects.filter(pk=self.link.pk).exists())

    def test_csrf_valid_token_preserves_json_menu_creation(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        client.get(reverse('meals:mealplan_create'))
        token=client.cookies['csrftoken'].value
        response=client.post(reverse('meals:add_diet_menu_api'),json.dumps({'date':'2026-11-06','meal_type':'석식','menu_name':'정상 메뉴'}),content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200)
        self.assertTrue(Menu.objects.filter(name='정상 메뉴').exists())

    def test_menu_delete_get_is_read_only(self):
        response=self.client.get(reverse('meals:menu_delete',args=[self.menu.pk]))
        self.assertEqual(response.status_code,405)
        self.assertTrue(Menu.objects.filter(pk=self.menu.pk).exists())

    def test_invalid_meal_type_does_not_create_plan_or_menu(self):
        response=self.post_json('add_diet_menu_api',{'date':'2026-11-07','meal_type':'invalid','menu_name':'invalid-menu'})
        self.assertEqual(response.status_code,400)
        self.assertFalse(Menu.objects.filter(name='invalid-menu').exists())
        self.assertFalse(DietPlan.objects.filter(target_date='2026-11-07').exists())

    def test_malformed_payload_is_validation_error(self):
        for data in [[],None,{'date':'bad','meal_type':'석식','menu_id':self.menu.pk}]:
            with self.subTest(data=data):self.assertEqual(self.post_json('add_diet_menu_api',data).status_code,400)

    def test_served_plan_cannot_add_or_remove_links(self):
        self.plan.is_served=True;self.plan.save()
        for name,data in [('add_diet_menu_api',{'date':'2026-11-06','meal_type':'석식','menu_name':'추가'}),
                          ('remove_diet_menu_api',{'date':'2026-11-06','meal_type':'석식','menu_id':self.menu.pk})]:
            with self.subTest(name=name):self.assertEqual(self.post_json(name,data).status_code,409)
        self.assertTrue(DietMenu.objects.filter(pk=self.link.pk).exists())

    def test_served_plan_delete_endpoint_preserves_cooking_history(self):
        from meals.models import CookingInstruction
        instruction=CookingInstruction.objects.create(diet_plan=self.plan,instructions='보존할 지시')
        self.plan.is_served=True;self.plan.save()
        self.assertEqual(self.client.post(reverse('meals:delete_diet_menu_api',args=[self.link.pk])).status_code,409)
        self.assertTrue(CookingInstruction.objects.filter(pk=instruction.pk).exists())

    def test_bulk_delete_cannot_remove_used_plan(self):
        self.plan.is_served=True;self.plan.save()
        self.client.post(reverse('meals:bulk_delete_mealplans'),{'start_date':'2026-11-01','end_date':'2026-11-30'})
        self.assertTrue(DietPlan.objects.filter(pk=self.plan.pk).exists())

    def test_bulk_delete_cannot_redirect_to_external_site(self):
        response=self.client.post(reverse('meals:bulk_delete_mealplans'),{'start_date':'2025-01-01','end_date':'2025-01-02','redirect_url':'https://evil.invalid/'})
        self.assertEqual(response.status_code,302)
        self.assertNotIn('evil.invalid',response['Location'])

    def test_public_signup_requires_admin_activation(self):
        client=Client()
        response=client.post(reverse('signup'),{'username':'verify-new-user','email':'new-user@example.invalid','password1':'Isolated-Test-Only-Pass-837!','password2':'Isolated-Test-Only-Pass-837!'})
        self.assertEqual(response.status_code,302)
        user=get_user_model().objects.get(username='verify-new-user')
        self.assertFalse(user.is_active)
        self.assertFalse(client.login(username='verify-new-user',password='Isolated-Test-Only-Pass-837!'))

    def test_bad_months_are_400_not_server_errors(self):
        routes=['meals:mealplan_list','meals:monthly_meal_plan_document','forecasting:prediction_calendar','inventory:monthly_inventory_report']
        for route in routes:
            for query in [{'year':'bad','month':'11'},{'year':'2026','month':'13'},{'year':'0','month':'1'}]:
                with self.subTest(route=route,query=query):
                    self.assertEqual(self.client.get(reverse(route),query).status_code,400)

    def test_workflow_order_appears_in_vendor_document(self):
        plan,item=self.issue()
        response=self.client.get(reverse('procurement:vendor_procurement_report'),{'start_date':'2026-11-06','end_date':'2026-11-06'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['total_item_count'],1)
        self.assertContains(response,self.ing.name)
        self.assertEqual(response.context['total_amount'],4500)

    def test_weekend_manual_order_is_not_dropped(self):
        plan=create_manual_plan([(self.ing.pk,'7')],date(2026,11,7),self.user,uuid.uuid4())
        confirm_orders(plan.pk,self.user)
        response=self.client.get(reverse('procurement:vendor_procurement_report'),{'start_date':'2026-11-07','end_date':'2026-11-07'})
        self.assertEqual(response.context['total_item_count'],1)

    def test_vendor_xlsx_shows_ordered_packages_not_shortage(self):
        plan,item=self.issue()
        response=self.client.get(reverse('procurement:export_vendor_procurement_excel'),{'start_date':'2026-11-06','end_date':'2026-11-06'})
        wb=openpyxl.load_workbook(io.BytesIO(response.content));rows=list(wb.active.values)
        self.assertEqual(len(rows),2)
        self.assertEqual((rows[1][6],rows[1][7],rows[1][9],rows[1][10]),('통',500,9,4500))

    def test_weekly_xlsx_uses_snapshot_package_amounts(self):
        self.issue()
        response=self.client.get(reverse('procurement:export_weekly_procurement_excel'),{'date':'2026-11-06'})
        row=list(openpyxl.load_workbook(io.BytesIO(response.content)).active.values)[1]
        self.assertEqual((row[5],row[6],row[8],row[9]),('통',500,9,4500))

    def test_vendor_name_with_excel_invalid_characters_exports(self):
        self.issue();self.vendor.name='검증[업체]/:*?긴이름';self.vendor.save()
        response=self.client.get(reverse('procurement:export_vendor_procurement_excel'),{'supplier_id':self.vendor.pk,'start_date':'2026-11-06','end_date':'2026-11-06'})
        self.assertEqual(response.status_code,200)
        self.assertLessEqual(len(openpyxl.load_workbook(io.BytesIO(response.content)).active.title),31)

    def test_untrusted_names_are_literal_in_all_workbooks(self):
        self.ing.name='=1+1';self.ing.save();self.menu.name='=2+2';self.menu.save()
        self.issue()
        routes=[('procurement:export_vendor_procurement_excel',{'start_date':'2026-11-06','end_date':'2026-11-06'}),
                ('procurement:export_weekly_procurement_excel',{'date':'2026-11-06'}),
                ('procurement:export_daily_inspection_excel',{'date':'2026-11-06'}),
                ('meals:export_weekly_mealplan_excel',{'start_date':'2026-11-02'})]
        for route,query in routes:
            with self.subTest(route=route):
                response=self.client.get(reverse(route),query);self.assertEqual(response.status_code,200)
                wb=openpyxl.load_workbook(io.BytesIO(response.content),data_only=False)
                self.assertFalse(any(c.data_type=='f' for ws in wb for row in ws for c in row))

    def test_invalid_supplier_identifier_is_not_500(self):
        for route in ['procurement:vendor_procurement_report','procurement:export_vendor_procurement_excel','procurement:daily_inspection_report']:
            with self.subTest(route=route):self.assertIn(self.client.get(reverse(route),{'supplier_id':'invalid'}).status_code,[400,404])

    def test_legacy_recipe_update_preserves_explicit_gram_unit(self):
        response=self.client.post(reverse('meals:menu_update',args=[self.menu.pk]),{'name':self.menu.name,'category':'기타','ingredient_id[]':[self.ing.pk],'ing_amount[]':['100']})
        self.assertEqual(response.status_code,302)
        recipe=Recipe.objects.get(menu=self.menu)
        self.assertEqual((recipe.required_amount,recipe.unit),(100,'g'))

    def test_invalid_recipe_edit_cannot_erase_previous_recipe(self):
        for amount in ['-1','NaN','Infinity']:
            with self.subTest(amount=amount):
                response=self.client.post(reverse('meals:menu_update',args=[self.menu.pk]),{'name':self.menu.name,'category':'기타','ingredient_id[]':[self.ing.pk],'ing_amount[]':[amount]})
                self.assertEqual(response.status_code,400)
                self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk,required_amount=100,unit='g').exists())

    def test_recipe_api_returns_recipe_unit_instead_of_stock_unit(self):
        response=self.client.get(reverse('meals:get_menu_recipes_api',args=[self.menu.pk]))
        data=response.json();rows=data.get('ingredients',data.get('recipes',[]))
        self.assertEqual(rows[0]['unit'],'g')

    def test_weekly_editor_supplies_csrf_cookie_and_header(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        response=client.get(reverse('meals:weekly_mealplan_create'),{'start_date':'2026-11-02'})
        self.assertIn('csrftoken',client.cookies)
        self.assertContains(response,'X-CSRFToken')

    def test_signup_cannot_escalate_role_or_staff(self):
        client=Client()
        client.post(reverse('signup'),{'username':'verify-untrusted','email':'untrusted@example.invalid','password1':'Isolated-Test-Only-Pass-837!','password2':'Isolated-Test-Only-Pass-837!','role':'ADMIN','is_staff':'1','is_active':'1'})
        user=get_user_model().objects.get(username='verify-untrusted')
        self.assertEqual(user.role,'NUTRITIONIST');self.assertFalse(user.is_staff);self.assertFalse(user.is_active)

    def test_monthly_base_unit_rate_matches_frozen_order_amount(self):
        self.issue()
        response=self.client.get(reverse('procurement:doc_monthly_settlement'),{'month':'2026-11'})
        row=response.context['item_details'][0]
        self.assertEqual((row['unit_price'],row['quantity'],row['amount']),(100,45,4500))

    def test_unused_menu_deletes_only_with_csrf_post(self):
        menu=Menu.objects.create(name='삭제 검증')
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        client.get(reverse('meals:menu_list'))
        response=client.post(reverse('meals:menu_delete',args=[menu.pk]),HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code,302)
        self.assertFalse(Menu.objects.filter(pk=menu.pk).exists())
