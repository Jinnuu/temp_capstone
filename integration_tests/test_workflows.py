import io
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.template import engines
from django.test import TestCase, SimpleTestCase
from django.urls import resolve, reverse
from openpyxl import Workbook, load_workbook

from inventory.models import Ingredient, InventoryLog
from inventory.services import process_ingredient_file_upload
from inventory.views import get_ingredient_stock_queryset
from meals.models import DietPlan, DietMenu, Menu, Recipe
from procurement.models import OrderItem, PurchaseOrder
from forecasting.models import AttendancePrediction


def workbook_file(rows, name='upload.xlsx', extra=None):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    if extra:
        sheet = wb.create_sheet('채소류')
        for row in extra:
            sheet.append(row)
    stream = io.BytesIO()
    wb.save(stream)
    return SimpleUploadedFile(name, stream.getvalue())


class WorkflowCase(TestCase):
    def setUp(self):
        self.supplier = get_user_model().objects.create_user(username='supplier', name='공급회사', role='SUPPLIER')
        self.ing = Ingredient.objects.create(name='쌀', unit='kg', unit_price=1000, safe_stock_level=5, supplier=self.supplier, description='기존 설명')
        self.menu = Menu.objects.create(name='쌀밥', category='밥')
        Recipe.objects.create(menu=self.menu, ingredient=self.ing, required_amount=Decimal('0.10'))
        self.monday = date(2026, 10, 12)

    def plan(self, day, meal='중식', headcount=100):
        plan = DietPlan.objects.create(target_date=day, meal_type=meal, headcount=headcount)
        DietMenu.objects.create(diet_plan=plan, menu=self.menu)
        return plan

    def stock(self, quantity, kind='입고'):
        InventoryLog.objects.create(ingredient=self.ing, log_type=kind, quantity=quantity)

    def smart(self, start, end=None, days=None):
        data = {'start_date': start.isoformat(), 'end_date': (end or start).isoformat(), 'days': days or ['0','1','2','3','4','5','6']}
        return self.client.get(reverse('procurement:order_from_mealplan'), data)

    def ordered_total(self, response):
        return sum((ing['order_qty'] for group in response.context['grouped_orders'] for plan in group['plans'] for menu in plan['menus'] for ing in menu['ingredients']), Decimal('0'))

    def test_single_ingredient_id_uses_annotated_stock(self):
        self.stock(3)
        response = self.client.get(reverse('procurement:order_create'), {'items': str(self.ing.pk)})
        self.assertEqual(response.context['shortage_map'], {'쌀': '2.00'})

    def test_comma_ids_use_all_inventory_log_types(self):
        self.stock(10); self.stock(2, '출고'); self.stock(4, '폐기'); self.stock(-1, '조정')
        second = Ingredient.objects.create(name='소금', unit='kg', safe_stock_level=2)
        response = self.client.get(reverse('procurement:order_create'), {'items': f'{self.ing.pk},{second.pk}'})
        self.assertEqual(response.context['shortage_map'], {'쌀': '2.00', '소금': '2.00'})

    def test_repeated_ids_and_nonshortage_do_not_force_minimum(self):
        self.stock(5)
        response = self.client.get(reverse('procurement:order_create'), {'items': [str(self.ing.pk), str(self.ing.pk), 'bad']})
        self.assertEqual(response.context['shortage_map'], {})

    def test_named_amounts_take_priority_over_date(self):
        with patch('procurement.views.get_all_day_requirements') as calc:
            response = self.client.get(reverse('procurement:order_create'), {'items': '쌀', 'amounts': '7.25', 'target_date': '2026-10-12'})
        calc.assert_not_called()
        self.assertEqual(response.context['shortage_map'], {'쌀': '7.25'})

    def test_date_requirement_fallback(self):
        with patch('procurement.views.get_all_day_requirements', return_value={'items': {'쌀': {'order_amount': 4}}}):
            response = self.client.get(reverse('procurement:order_create'), {'target_date': '2026-10-12'})
        self.assertEqual(response.context['shortage_map'], {'쌀': '4'})

    def test_dashboard_total_is_not_capped_at_eight(self):
        for i in range(10):
            Ingredient.objects.create(name=f'부족재료{i}', unit='kg', safe_stock_level=1)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_low_stock_count'], 11)
        self.assertEqual(len(response.context['low_stock_items']), 8)

    def test_preserved_release_patch_routes(self):
        from inventory.release_patch_views import ingredient_upload_flexible
        from meals.release_patch_views import deduct_inventory_view, recipe_upload_page
        for name, function in [('inventory:ingredient_upload', ingredient_upload_flexible), ('inventory:ingredient_upload_legacy', ingredient_upload_flexible), ('meals:deduct_inventory', deduct_inventory_view), ('meals:recipe_upload_page', recipe_upload_page)]:
            self.assertIs(resolve(reverse(name)).func, function)

    def test_titled_multisheet_ingredient_upload_matches_supplier_name(self):
        upload = workbook_file([['2026 식재료 기준정보'], ['품목명', '발주처', '식품 설명', '단가 (원)'], ['쌀', '공급회사', '수정 설명', '1,200']], extra=[['재료명', '안전재고'], ['당근', 3]])
        response = self.client.post(reverse('inventory:ingredient_upload'), {'file': upload})
        self.assertEqual(response.status_code, 302)
        self.ing.refresh_from_db()
        self.assertEqual(self.ing.supplier, self.supplier)
        self.assertEqual(self.ing.description, '수정 설명')
        self.assertEqual(self.ing.unit_price, 1200)
        self.assertEqual(self.ing.safe_stock_level, 5)
        self.assertEqual(Ingredient.objects.get(name='당근').category, '채소류')

    def test_csv_ingredient_upload_preserves_missing_columns(self):
        upload = SimpleUploadedFile('ingredients.csv', '식재료명,단가\n쌀,800\n'.encode('cp949'))
        response = self.client.post(reverse('inventory:ingredient_upload_legacy'), {'file': upload})
        self.assertEqual(response.status_code, 302)
        self.ing.refresh_from_db()
        self.assertEqual((self.ing.unit_price, self.ing.safe_stock_level, self.ing.description, self.ing.supplier_id), (800, 5, '기존 설명', self.supplier.pk))

    def test_ingredient_upload_rolls_back_on_bad_number(self):
        upload = workbook_file([['식재료명', '단가'], ['쌀', 800], ['새재료', 'invalid']])
        with self.assertRaises(ValueError):
            process_ingredient_file_upload(upload)
        self.ing.refresh_from_db()
        self.assertEqual(self.ing.unit_price, 1000)
        self.assertFalse(Ingredient.objects.filter(name='새재료').exists())

    def test_unknown_supplier_does_not_erase_existing_mapping(self):
        with self.assertRaises(ValueError):
            process_ingredient_file_upload(workbook_file([['식재료명','발주처'], ['쌀','미등록회사']]))
        self.ing.refresh_from_db(); self.assertEqual(self.ing.supplier, self.supplier)

    def test_recipe_release_upload_to_deduction_flow_is_idempotent(self):
        upload = workbook_file([['레시피 자료'], ['메뉴명', '식재료명', '사용량', '단위'], ['쌀밥', '쌀', '0.2', 'kg']])
        response = self.client.post(reverse('meals:recipe_upload_page'), {'file': upload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recipe.objects.get(menu=self.menu, ingredient=self.ing).required_amount, Decimal('0.2'))
        plan = self.plan(self.monday, headcount=10); self.stock(20)
        preview = self.client.get(reverse('meals:deduct_inventory'), {'date': str(self.monday)})
        self.assertEqual(preview.context['rows'][0]['deduct_qty'], Decimal('2'))
        payload = {'target_date': str(self.monday), 'confirm': '1'}
        self.client.post(reverse('meals:deduct_inventory'), payload)
        self.client.post(reverse('meals:deduct_inventory'), payload)
        self.assertEqual(InventoryLog.objects.filter(log_type='출고').count(), 1)
        plan.refresh_from_db(); self.assertTrue(plan.is_served)
        self.assertEqual(get_ingredient_stock_queryset().get(pk=self.ing.pk).calc_stock, 18)

    def test_weekday_order_group_uses_dinner_then_next_breakfast_lunch(self):
        self.plan(self.monday, '중식'); self.plan(self.monday, '석식')
        self.plan(self.monday + timedelta(days=1), '조식'); self.plan(self.monday + timedelta(days=1), '중식'); self.plan(self.monday + timedelta(days=1), '석식')
        response = self.smart(self.monday)
        plans = response.context['grouped_orders'][0]['plans']
        self.assertEqual([(x['target_date'],x['meal_type']) for x in plans], [(self.monday,'석식'), (self.monday+timedelta(days=1),'조식'), (self.monday+timedelta(days=1),'중식')])
        self.assertEqual(self.ordered_total(response), 35) # 3 * 10kg + 5kg reserve

    def test_friday_group_covers_weekend_and_next_monday(self):
        friday=self.monday+timedelta(days=4)
        for i in range(4):
            for meal in ['조식','중식','석식']:
                self.plan(friday+timedelta(days=i),meal)
        response=self.smart(friday,friday+timedelta(days=2))
        groups=response.context['grouped_orders']
        self.assertEqual(len(groups),1)
        self.assertEqual(len(groups[0]['plans']),9)
        self.assertEqual(self.ordered_total(response),95)

    def test_weekend_only_has_no_order_day_group(self):
        saturday=self.monday+timedelta(days=5);self.plan(saturday)
        self.assertEqual(self.smart(saturday).context['grouped_orders'], [])

    def test_selected_weekday_and_no_duplicate_meals(self):
        for i in range(3):
            for meal in ['조식','중식','석식']:
                self.plan(self.monday+timedelta(days=i),meal)
        response=self.smart(self.monday,self.monday+timedelta(days=1))
        plans=[(p['target_date'],p['meal_type']) for g in response.context['grouped_orders'] for p in g['plans']]
        self.assertEqual(len(plans),len(set(plans)))
        response=self.smart(self.monday,self.monday+timedelta(days=1),['1'])
        self.assertEqual([g['order_date'] for g in response.context['grouped_orders']], [self.monday+timedelta(days=1)])

    def test_safety_reserve_not_duplicated_across_menus_or_days(self):
        extra=Menu.objects.create(name='추가쌀밥');Recipe.objects.create(menu=extra,ingredient=self.ing,required_amount=Decimal('0.10'))
        first=self.plan(self.monday,'석식',100);DietMenu.objects.create(diet_plan=first,menu=extra)
        self.plan(self.monday+timedelta(days=1),'석식',100)
        self.stock(8)
        self.assertEqual(self.ordered_total(self.smart(self.monday,self.monday+timedelta(days=1))),Decimal('27')) # 30+5-8

    def test_sufficient_stock_yields_no_order(self):
        self.stock(50);self.plan(self.monday,'석식')
        self.assertEqual(self.ordered_total(self.smart(self.monday)),0)

    def test_predicted_headcount_is_used_in_smart_order(self):
        self.plan(self.monday,'석식',5)
        AttendancePrediction.objects.create(prediction_date=self.monday, meal_type='dinner', predicted_count=30, model_name='fixture')
        response=self.smart(self.monday)
        self.assertEqual(response.context['grouped_orders'][0]['plans'][0]['serving_count'],30)
        self.assertEqual(self.ordered_total(response),8)

    def test_order_creation_receipt_and_repeated_confirmation(self):
        payload={'ingredient_id[]':[str(self.ing.pk)],'quantity[]':['2.5'],'target_date[]':[str(self.monday)],'meal_type[]':['중식']}
        response=self.client.post(reverse('procurement:order_from_mealplan'),payload)
        self.assertEqual(response.status_code,302)
        order=PurchaseOrder.objects.get();item=order.items.get()
        self.assertEqual((order.supplier_id,order.total_amount,item.required_qty),(self.supplier.pk,2500,Decimal('2.5')))
        for _ in range(2):self.client.post(reverse('procurement:order_status_update',args=[order.pk]),{'status':'완료'})
        self.assertEqual(InventoryLog.objects.filter(log_type='입고').count(),1)
        self.assertEqual(get_ingredient_stock_queryset().get(pk=self.ing.pk).calc_stock,Decimal('2.5'))

    def test_simple_order_preserves_post_date(self):
        self.client.post(reverse('procurement:order_create'),{'ingredient_id[]':[str(self.ing.pk)],'quantity[]':['2'],'target_date':str(self.monday)})
        self.assertEqual(OrderItem.objects.get().target_date,self.monday)

    def test_wide_upload_keeps_headcount_and_row_upload_overwrites(self):
        upload=SimpleUploadedFile('wide.csv', '날짜,조식,기준식수_조식,중식,기준식수_중식\n2026-10-12,쌀밥,50,쌀밥,80\n'.encode())
        self.client.post(reverse('meals:mealplan_bulk_upload'),{'mealplan_file':upload})
        self.assertEqual(DietPlan.objects.get(meal_type='조식').headcount,50)
        self.assertEqual(DietPlan.objects.get(meal_type='중식').headcount,80)
        upload=SimpleUploadedFile('row.csv','date,meal_type,menu_name,headcount\n2026-10-12,중식,새메뉴,90\n'.encode())
        self.client.post(reverse('meals:mealplan_bulk_upload'),{'mealplan_file':upload})
        self.assertEqual(list(DietPlan.objects.get(meal_type='중식').diet_menus.values_list('menu__name',flat=True)),['새메뉴'])

    def test_new_menu_name_api_and_delete_endpoint(self):
        response=self.client.post(reverse('meals:add_diet_menu_api'),data=json.dumps({'date':str(self.monday),'meal_type':'중식','menu_name':'새메뉴'}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        identifier=response.json()['menus'][0]['diet_menu_id']
        response=self.client.post(reverse('meals:delete_diet_menu_api',args=[identifier]))
        self.assertEqual(response.status_code,200)
        self.assertFalse(DietMenu.objects.filter(pk=identifier).exists())

    def test_weekly_recipe_document_links_menu_recipe_and_explicit_headcount(self):
        self.plan(self.monday)
        response=self.client.get(reverse('meals:weekly_recipe_report'),{'start_date':str(self.monday),'end_date':str(self.monday),'headcount':'40'})
        self.assertEqual(response.status_code,200)
        entry=response.context['report_data'][0]['menus'][0]['ingredients'][0]
        self.assertEqual((entry['name'],entry['needed_qty']),('쌀',4))
        # This verifies only the recipe quantity document, not a cooking instruction workflow.

    def test_all_documents_and_main_screens_render(self):
        self.plan(self.monday)
        order=PurchaseOrder.objects.create(supplier=self.supplier,total_amount=1000)
        OrderItem.objects.create(purchase_order=order,ingredient=self.ing,target_date=self.monday,meal_type='중식',required_qty=1,missing_qty=1,order_unit_price=1000,estimated_price=1000)
        names=['docs_index','inventory:ingredient_list','inventory:ingredient_upload','inventory:weekly_inventory_report','inventory:monthly_inventory_report','inventory:doc_inventory_status','meals:mealplan_create','meals:mealplan_list','meals:weekly_mealplan_create','meals:monthly_mealplan_create','meals:mealplan_bulk_upload','meals:recipe_upload_page','meals:weekly_meal_plan_document','meals:monthly_meal_plan_document','meals:weekly_recipe_report','meals:doc_menu_overview','procurement:order_create','procurement:order_list','procurement:weekly_procurement_report','procurement:vendor_procurement_report','procurement:daily_inspection_report','procurement:doc_purchase_requisition','procurement:doc_inspection_log','login','forecasting:prediction_list']
        for name in names:
            with self.subTest(route=name):
                response=self.client.get(reverse(name),{'date':str(self.monday),'start_date':str(self.monday),'end_date':str(self.monday)})
                self.assertEqual(response.status_code,200)

    def test_excel_exports_open_as_real_workbooks(self):
        self.plan(self.monday)
        for name in ['meals:export_weekly_mealplan_excel','inventory:export_inventory_excel','procurement:export_weekly_procurement_excel','procurement:export_vendor_procurement_excel','procurement:export_daily_inspection_excel']:
            with self.subTest(route=name):
                response=self.client.get(reverse(name),{'date':str(self.monday),'start_date':str(self.monday),'end_date':str(self.monday)})
                self.assertEqual(response.status_code,200)
                wb=load_workbook(io.BytesIO(response.content));self.assertTrue(wb.sheetnames)

    def test_migration_graph_has_no_conflicts(self):
        executor=MigrationExecutor(connection)
        self.assertEqual(executor.loader.detect_conflicts(),{})
        self.assertEqual(executor.migration_plan(executor.loader.graph.leaf_nodes()),[])

    def test_legacy_xls_ingredient_upload(self):
        import xlwt
        wb=xlwt.Workbook();ws=wb.add_sheet('곡류')
        for row_index,row in enumerate([['식재료명','발주처','단가'],['쌀','공급회사',1500]]):
            for col_index,value in enumerate(row):ws.write(row_index,col_index,value)
        stream=io.BytesIO();wb.save(stream)
        self.client.post(reverse('inventory:ingredient_upload'),{'file':SimpleUploadedFile('legacy.xls',stream.getvalue())})
        self.ing.refresh_from_db();self.assertEqual(self.ing.unit_price,1500)
        self.assertEqual(self.ing.supplier,self.supplier)

    def test_weekly_page_keeps_search_and_next_monday_editing(self):
        next_monday=self.monday+timedelta(days=7);self.plan(next_monday,'조식')
        response=self.client.get(reverse('meals:weekly_mealplan_create'),{'start_date':str(self.monday)})
        self.assertContains(response,'다음 월요일 조식·중식')
        self.assertContains(response,f'data-date="{next_monday}" data-meal-type="조식"')
        self.assertContains(response,'메뉴 검색')

    def test_real_prediction_through_order_receipt_deduction_and_report(self):
        from forecasting.services.prediction_service import run_attendance_prediction
        prediction=run_attendance_prediction(self.monday,'dinner',menu_text='쌀밥 미역국')
        plan=self.plan(self.monday,'석식',headcount=prediction.predicted_count)
        response=self.smart(self.monday)
        quantity=response.context['grouped_orders'][0]['plans'][0]['menus'][0]['ingredients'][0]['order_qty']
        required=Decimal(prediction.predicted_count)*Decimal('0.10')
        self.assertEqual(quantity,required+Decimal('5'))
        self.client.post(reverse('procurement:order_from_mealplan'),{'ingredient_id[]':[str(self.ing.pk)],'quantity[]':[str(quantity)],'target_date[]':[str(self.monday)],'meal_type[]':['석식']})
        order=PurchaseOrder.objects.get()
        self.client.post(reverse('procurement:order_status_update',args=[order.pk]),{'status':'완료'})
        self.client.post(reverse('meals:deduct_inventory'),{'target_date':str(self.monday),'meal_type':'석식','confirm':'1'})
        self.assertEqual(get_ingredient_stock_queryset().get(pk=self.ing.pk).calc_stock,Decimal('5'))
        response=self.client.get(reverse('meals:weekly_recipe_report'),{'start_date':str(self.monday),'end_date':str(self.monday),'headcount':prediction.predicted_count})
        self.assertEqual(Decimal(str(response.context['report_data'][0]['menus'][0]['ingredients'][0]['needed_qty'])),required)

    def test_bulk_delete_requires_post_and_preserves_other_dates(self):
        first=self.plan(self.monday);second=self.plan(self.monday+timedelta(days=7))
        data={'start_date':str(self.monday),'end_date':str(self.monday)}
        self.assertEqual(self.client.get(reverse('meals:bulk_delete_mealplans'),data).status_code,405)
        self.assertTrue(DietPlan.objects.filter(pk=first.pk).exists())
        self.assertEqual(self.client.post(reverse('meals:bulk_delete_mealplans'),data).status_code,302)
        self.assertFalse(DietPlan.objects.filter(pk=first.pk).exists())
        self.assertTrue(DietPlan.objects.filter(pk=second.pk).exists())
