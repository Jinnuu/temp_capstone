import uuid
from datetime import date,timedelta,datetime,timezone as datetime_timezone
from decimal import Decimal
from django.test import TestCase,Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Ingredient,InventoryLog,SupplySpecification,IngredientCategory
from meals.models import DietPlan,DietMenu,Menu,Recipe
from procurement.models import ProcurementPlan,PurchaseOrder,GoodsInspection
from procurement.workflow import (quantity,convert,current_stock,build_preview,save_headcount,
                                  create_plan,confirm_orders,inspect_item,record_inventory)


class RequirementWorkflows(TestCase):
    def setUp(self):
        User=get_user_model()
        self.operator=User.objects.create_user(username='nutritionist',is_staff=True,name='영양사')
        self.vendor=User.objects.create_user(username='z-vendor',name='가업체',role='SUPPLIER')
        self.client.force_login(self.operator)
        self.ing=Ingredient.objects.create(name='참치',unit='kg',safe_stock_level=0,unit_price=100,supplier=self.vendor,category='통조림')
        self.menu=Menu.objects.create(name='참치볶음')
        self.recipe=Recipe.objects.create(menu=self.menu,ingredient=self.ing,required_amount=100,unit='g')
        self.plan=DietPlan.objects.create(target_date=date(2026,10,16),meal_type='석식',headcount=100)
        DietMenu.objects.create(diet_plan=self.plan,menu=self.menu)
        self.spec=SupplySpecification.objects.create(ingredient=self.ing,supplier=self.vendor,label='5kg / 캔',base_quantity=5,base_unit='kg',order_unit='캔',unit_price=500)

    def ready(self,count=351):
        save_headcount(self.plan.pk,count,count)
        return create_plan(self.plan.target_date,self.plan.target_date,self.operator,uuid.uuid4())

    def order(self,count=351):
        return confirm_orders(self.ready(count).pk,self.operator)[0]

    def test_manual_and_final_headcounts_store_zero_and_timestamp(self):
        save_headcount(self.plan.pk,0,0);self.plan.refresh_from_db()
        self.assertEqual((self.plan.headcount,self.plan.final_headcount),(0,0))
        self.assertIsNotNone(self.plan.headcount_confirmed_at)
        self.assertEqual(build_preview(self.plan.target_date,self.plan.target_date)['lines'],[])

    def test_negative_nan_infinity_fractional_headcount_rejected(self):
        for value in ['-1','NaN','Infinity','1.5','abc']:
            with self.subTest(value=value),self.assertRaises(ValidationError):save_headcount(self.plan.pk,value,value)
        self.plan.refresh_from_db();self.assertIsNone(self.plan.final_headcount)

    def test_manual_change_clears_confirmation(self):
        save_headcount(self.plan.pk,10,12);save_headcount(self.plan.pk,11)
        self.plan.refresh_from_db();self.assertIsNone(self.plan.final_headcount)

    def test_ai_absent_manual_confirmation_and_ui(self):
        response=self.client.post(reverse('procurement:workflow'),{'plan':self.plan.pk,'manual':350,'final':350,'confirm':'on'})
        self.assertEqual(response.status_code,302);self.plan.refresh_from_db();self.assertEqual(self.plan.final_headcount,350)
        self.assertContains(self.client.get(reverse('procurement:workflow')),'미생성 / 수동 입력 가능')

    def test_final_confirmation_overrides_ai(self):
        from forecasting.models import AttendancePrediction
        from procurement.views import get_serving_count
        AttendancePrediction.objects.create(prediction_date=self.plan.target_date,meal_type='dinner',predicted_count=999,model_name='test')
        save_headcount(self.plan.pk,300,350);self.plan.refresh_from_db()
        self.assertEqual(get_serving_count(self.plan)[0],350)

    def test_no_final_headcount_blocks_snapshot(self):
        with self.assertRaises(ValidationError):create_plan(self.plan.target_date,self.plan.target_date,self.operator,uuid.uuid4())
        self.assertEqual(ProcurementPlan.objects.count(),0)

    def test_explicit_mass_conversion_and_seven_can_example(self):
        plan=self.ready(350);line=plan.lines.get()
        self.assertEqual((line.needed_qty,line.package_quantity),(Decimal('35'),7))
        self.assertEqual(convert(700,'g','kg'),Decimal('.7'))
        self.assertEqual(convert(1,'EA','개'),1)
        self.assertEqual(line.unit_price,500)

    def test_round_up_and_manual_adjustment_snapshot(self):
        plan=self.ready(351);line=plan.lines.get()
        self.assertEqual(line.package_quantity,8)
        order=confirm_orders(plan.pk,self.operator,{str(line.pk):'9'})[0];item=order.items.get()
        self.assertEqual((item.package_quantity,item.required_qty,item.estimated_price),(9,45,4500))
        self.assertEqual(item.spec_snapshot,'5kg / 캔')

    def test_zero_negative_noninteger_or_underorder_adjustment_rejected(self):
        plan=self.ready();line=plan.lines.get()
        for value in ['-1','0','7','8.5','NaN']:
            with self.subTest(value=value),self.assertRaises(ValidationError):confirm_orders(plan.pk,self.operator,{str(line.pk):value})
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_duplicate_plan_and_confirm_requests_create_once(self):
        save_headcount(self.plan.pk,350,350);key=uuid.uuid4()
        first=create_plan(self.plan.target_date,self.plan.target_date,self.operator,key)
        second=create_plan(self.plan.target_date,self.plan.target_date,self.operator,key)
        self.assertEqual(first.pk,second.pk)
        self.assertEqual(confirm_orders(first.pk,self.operator)[0].pk,confirm_orders(first.pk,self.operator)[0].pk)
        self.assertEqual(PurchaseOrder.objects.count(),1)

    def test_missing_spec_and_supplier_block_with_named_errors(self):
        self.spec.delete();save_headcount(self.plan.pk,350,350)
        result=build_preview(self.plan.target_date,self.plan.target_date)
        self.assertTrue(any('참치' in error and '납품' in error for error in result['errors']))
        self.ing.supplier=None;self.ing.save()
        self.assertTrue(any('공급업체' in error for error in build_preview(self.plan.target_date,self.plan.target_date)['errors']))

    def test_incompatible_units_and_recipe_missing_block(self):
        save_headcount(self.plan.pk,350,350)
        self.recipe.unit='EA';self.recipe.save()
        self.assertTrue(any('단위 환산 불가' in error for error in build_preview(self.plan.target_date,self.plan.target_date)['errors']))
        self.recipe.delete()
        self.assertTrue(any('레시피' in error for error in build_preview(self.plan.target_date,self.plan.target_date)['errors']))

    def test_pack_description_is_not_parsed_without_coefficient(self):
        self.spec.base_quantity=Decimal('.7');self.spec.base_unit='kg';self.spec.label='700g(70g×10개)';self.spec.save()
        line=self.ready(351).lines.get()
        self.assertEqual(line.package_quantity,51)

    def test_repeated_ingredient_aggregated_safety_applied_once(self):
        self.ing.safe_stock_level=5;self.ing.save()
        extra=Menu.objects.create(name='추가참치');Recipe.objects.create(menu=extra,ingredient=self.ing,required_amount=100,unit='g');DietMenu.objects.create(diet_plan=self.plan,menu=extra)
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=8)
        line=self.ready(100).lines.get()
        self.assertEqual((line.needed_qty,line.shortage_qty,line.package_quantity),(20,17,4))

    def test_stock_surplus_yields_zero_order(self):
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=100)
        plan=self.ready(100);self.assertEqual(plan.lines.get().package_quantity,0)
        self.assertEqual(confirm_orders(plan.pk,self.operator),[])

    def test_friday_group_and_weekend_only(self):
        for offset in range(1,4):
            for meal in ['조식','중식','석식']:
                p=DietPlan.objects.create(target_date=self.plan.target_date+timedelta(days=offset),meal_type=meal,headcount=1,final_headcount=1)
                DietMenu.objects.create(diet_plan=p,menu=self.menu)
        save_headcount(self.plan.pk,1,1)
        result=build_preview(self.plan.target_date,self.plan.target_date)
        self.assertEqual(len(result['meal_ids']),9)
        self.assertEqual(result['lines'][0]['needed_qty'],Decimal('.9'))
        self.assertTrue(build_preview(self.plan.target_date+timedelta(days=1),self.plan.target_date+timedelta(days=2))['errors'])

    def test_changed_headcount_recipe_or_spec_marks_review(self):
        plan=self.ready();save_headcount(self.plan.pk,100,100)
        plan.refresh_from_db();self.assertTrue(plan.needs_review)
        with self.assertRaises(ValidationError):confirm_orders(plan.pk,self.operator)
        plan=self.ready();self.recipe.required_amount=101;self.recipe.save()
        plan.refresh_from_db();self.assertTrue(plan.needs_review)

    def test_stock_change_since_preview_requires_recalculation(self):
        plan=self.ready();InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=1)
        with self.assertRaises(ValidationError):confirm_orders(plan.pk,self.operator)

    def test_no_receipt_before_inspection_and_legacy_cannot_bypass(self):
        order=self.order();self.assertEqual(current_stock(self.ing),0)
        response=self.client.post(reverse('procurement:order_status_update',args=[order.pk]),{'status':'완료'})
        self.assertRedirects(response,reverse('procurement:workflow_inspections'))
        self.assertEqual(current_stock(self.ing),0)

    def test_inspection_partial_acceptance_and_duplicate_receipt(self):
        order=self.order();item=order.items.get()
        first=inspect_item(item.pk,self.operator,40,35,'이상','5kg / 캔','5kg 품질 불량')
        second=inspect_item(item.pk,self.operator,40,35,'이상','5kg / 캔','5kg 품질 불량')
        self.assertEqual(first.pk,second.pk);self.assertEqual(current_stock(self.ing),35)
        self.assertEqual(InventoryLog.objects.count(),1)
        order.refresh_from_db();self.assertEqual(order.status,'완료')

    def test_conflicting_reinspection_does_not_overwrite(self):
        item=self.order().items.get();inspect_item(item.pk,self.operator,40,40,'정상','5kg / 캔')
        with self.assertRaises(ValidationError):inspect_item(item.pk,self.operator,40,39,'이상','5kg / 캔','수정')
        self.assertEqual(current_stock(self.ing),40)

    def test_invalid_inspections_never_receive_stock(self):
        item=self.order().items.get()
        cases=[(-1,0,'정상','spec',''),(40,41,'정상','spec',''),(40,40,'정상','',''),(39,39,'정상','spec',''),(40,1,'반품','spec','반품')]
        for args in cases:
            with self.subTest(args=args),self.assertRaises(ValidationError):inspect_item(item.pk,self.operator,*args)
        with self.assertRaises(ValidationError):inspect_item(item.pk,self.operator,40,40,'정상','spec',expiration=timezone.localdate()-timedelta(days=1))
        self.assertEqual(current_stock(self.ing),0);self.assertFalse(GoodsInspection.objects.exists())

    def test_inventory_request_idempotency_and_shortage(self):
        now=timezone.now();key=uuid.uuid4()
        a=record_inventory(self.ing.pk,'입고',10,self.operator,key,now,notes='쌀 선입고')
        b=record_inventory(self.ing.pk,'입고',10,self.operator,key,now,notes='쌀 선입고')
        self.assertEqual(a.pk,b.pk)
        with self.assertRaises(ValidationError):record_inventory(self.ing.pk,'출고',11,self.operator,uuid.uuid4(),now)
        self.assertEqual(current_stock(self.ing),10)

    def test_deduction_blocks_short_stock_and_negative_headcount(self):
        save_headcount(self.plan.pk,100,100)
        data={'target_date':str(self.plan.target_date),'meal_type':'석식','confirm':'1'}
        self.client.post(reverse('meals:deduct_inventory'),data)
        self.assertFalse(InventoryLog.objects.filter(log_type='출고').exists())
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=10)
        self.client.post(reverse('meals:deduct_inventory'),dict(data,headcount='-1'))
        self.assertFalse(InventoryLog.objects.filter(log_type='출고').exists())
        self.client.post(reverse('meals:deduct_inventory'),data)
        self.client.post(reverse('meals:deduct_inventory'),data)
        self.assertEqual(InventoryLog.objects.filter(log_type='출고').count(),1)
        self.assertEqual(current_stock(self.ing),0)

    def test_category_rename_reclassifies_and_duplicate_shows_error(self):
        self.client.post(reverse('procurement:workflow_categories'),{'name':'공산품','rename_from':'통조림','ingredients':[self.ing.pk]})
        self.ing.refresh_from_db();self.assertEqual(self.ing.category,'공산품')
        response=self.client.post(reverse('procurement:workflow_categories'),{'name':'공산품'})
        self.assertContains(response,'이미 존재하는 분류')

    def test_supplier_and_spec_edit_from_ui(self):
        response=self.client.post(reverse('procurement:workflow_supplier_edit',args=[self.vendor.pk]),{'username':self.vendor.username,'name':'새업체','phone_number':'010'})
        self.assertEqual(response.status_code,302);self.vendor.refresh_from_db();self.assertEqual(self.vendor.name,'새업체')
        response=self.client.post(reverse('procurement:workflow_spec_edit',args=[self.spec.pk]),{'ingredient':self.ing.pk,'supplier':self.vendor.pk,'label':'700g(70g×10개)','base_quantity':700,'base_unit':'g','order_unit':'봉','order_increment':1,'unit_price':70})
        self.assertEqual(response.status_code,302);self.spec.refresh_from_db();self.assertEqual(self.spec.base_quantity,700)

    def test_inspection_ui_and_actual_monthly_settlement(self):
        order=self.order();item=order.items.get()
        response=self.client.post(reverse('procurement:workflow_inspection',args=[item.pk]),{'delivered':40,'accepted':35,'condition':'이상','specification':'5kg','notes':'5kg 반품'})
        self.assertEqual(response.status_code,302)
        response=self.client.get(reverse('procurement:workflow_settlement'),{'month':timezone.localdate().strftime('%Y-%m')})
        self.assertEqual(response.status_code,200)
        row=response.context['rows'][0];self.assertEqual(row['inspected_amount'],3500)
        self.assertEqual(row['uninspected'],0)

    def test_weekly_ledger_opening_waste_adjustment_and_closing(self):
        # UTC Oct 15 16:00 is Seoul Oct 16 01:00. Query business dates,
        # not now.date() (UTC), so this test is independent of execution time.
        now=datetime(2026,10,15,16,tzinfo=datetime_timezone.utc)
        record_inventory(self.ing.pk,'입고',10,self.operator,uuid.uuid4(),now-timedelta(days=8))
        record_inventory(self.ing.pk,'입고',2,self.operator,uuid.uuid4(),now)
        record_inventory(self.ing.pk,'폐기',1,self.operator,uuid.uuid4(),now)
        with timezone.override('Asia/Seoul'):
            business_date=timezone.localdate(now)
            response=self.client.get(reverse('procurement:workflow_ledger'),{'start_date':str(business_date-timedelta(days=1)),'end_date':str(business_date)})
            row=response.context['rows'][0];self.assertEqual((row['opening'],row['incoming'],row['waste'],row['closing']),(10,2,1,11))
            # The two new transactions are outside Oct 15 in business time.
            response=self.client.get(reverse('procurement:workflow_ledger'),{'start_date':'2026-10-15','end_date':'2026-10-15'})
            row=response.context['rows'][0];self.assertEqual((row['opening'],row['incoming'],row['waste'],row['closing']),(10,0,0,10))
        with timezone.override('UTC'):
            response=self.client.get(reverse('procurement:workflow_ledger'),{'start_date':'2026-10-15','end_date':'2026-10-15'})
            row=response.context['rows'][0];self.assertEqual((row['opening'],row['incoming'],row['waste'],row['closing']),(10,2,1,11))

    def test_complete_ui_headcount_snapshot_order_inspection_usage_flow(self):
        self.client.post(reverse('procurement:workflow'),{'plan':self.plan.pk,'manual':350,'final':350,'confirm':'on'})
        response=self.client.post(reverse('procurement:workflow_preview'),{'start_date':str(self.plan.target_date),'end_date':str(self.plan.target_date),'days':['4'],'request_key':str(uuid.uuid4()),'save':'1'})
        self.assertEqual(response.status_code,302);snapshot=ProcurementPlan.objects.get()
        response=self.client.post(reverse('procurement:workflow_plan',args=[snapshot.pk]));self.assertEqual(response.status_code,302)
        order=PurchaseOrder.objects.get();item=order.items.get()
        self.client.post(reverse('procurement:workflow_inspection',args=[item.pk]),{'delivered':35,'accepted':35,'condition':'정상','specification':'5kg / 캔'})
        self.client.post(reverse('meals:deduct_inventory'),{'target_date':str(self.plan.target_date),'meal_type':'석식','confirm':'1'})
        self.assertEqual(current_stock(self.ing),0)
        self.assertContains(self.client.get(reverse('procurement:workflow_plan',args=[snapshot.pk])),'업체별 구매발주서')

    def test_business_authentication_and_admin_permissions(self):
        anonymous=Client();self.assertEqual(anonymous.get(reverse('procurement:workflow')).status_code,302)
        self.assertEqual(anonymous.get(reverse('procurement:order_list')).status_code,302)
        self.client.force_login(self.vendor);self.assertEqual(self.client.get(reverse('procurement:workflow')).status_code,403)
        user=get_user_model().objects.create_user(username='ordinary')
        # Explicit server-side RBAC now rejects instead of redirecting to login.
        self.client.force_login(user);self.assertEqual(self.client.get(reverse('procurement:workflow_specs')).status_code,403)

    def test_all_new_ui_routes_render(self):
        for name in ['workflow','workflow_preview','workflow_inspections','workflow_transaction','workflow_ledger','workflow_settlement','workflow_specs','workflow_suppliers','workflow_categories','workflow_recipes']:
            with self.subTest(name=name):self.assertEqual(self.client.get(reverse('procurement:'+name)).status_code,200)

    def test_recipe_unit_and_cooking_notes_ui(self):
        response=self.client.post(reverse('procurement:workflow_recipe_edit',args=[self.recipe.pk]),{'menu':self.menu.pk,'ingredient':self.ing.pk,'required_amount':70,'unit':'g','cooking_notes':'충분히 익혀 제공'})
        self.assertEqual(response.status_code,302)
        self.recipe.refresh_from_db();self.menu.refresh_from_db()
        self.assertEqual((self.recipe.unit,self.recipe.required_amount),('g',70))
        self.assertEqual(self.menu.cooking_notes,'충분히 익혀 제공')

    def test_fifo_allocates_oldest_receipt_and_tracks_expiry(self):
        from inventory.models import StockLot,StockAllocation
        now=timezone.now()
        first=record_inventory(self.ing.pk,'입고',3,self.operator,uuid.uuid4(),now-timedelta(days=1),expiration=now.date()+timedelta(days=3))
        second=record_inventory(self.ing.pk,'입고',4,self.operator,uuid.uuid4(),now,expiration=now.date()+timedelta(days=5))
        out=record_inventory(self.ing.pk,'출고',5,self.operator,uuid.uuid4(),now)
        self.assertEqual(list(out.lot_allocations.order_by('lot_id').values_list('quantity',flat=True)),[Decimal('3'),Decimal('2')])
        self.assertEqual(StockLot.objects.get(incoming_log=first).remaining_quantity,0)
        self.assertEqual(StockLot.objects.get(incoming_log=second).remaining_quantity,2)

    def test_expired_lot_cannot_be_consumed_but_can_be_disposed(self):
        now=timezone.now()
        record_inventory(self.ing.pk,'입고',3,self.operator,uuid.uuid4(),now-timedelta(days=3),expiration=now.date()-timedelta(days=1))
        with self.assertRaises(ValidationError):record_inventory(self.ing.pk,'출고',1,self.operator,uuid.uuid4(),now)
        self.assertEqual(current_stock(self.ing),3)
        record_inventory(self.ing.pk,'폐기',3,self.operator,uuid.uuid4(),now)
        self.assertEqual(current_stock(self.ing),0)

    def test_ai_failure_does_not_block_manual_workflow(self):
        from unittest.mock import patch
        with patch('forecasting.views.run_attendance_prediction',side_effect=RuntimeError('모델 미가용')):
            response=self.client.post(reverse('forecasting:prediction_create'),{'prediction_date':str(self.plan.target_date)})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'실패')
        save_headcount(self.plan.pk,350,350)
        self.assertEqual(self.ready(350).lines.get().package_quantity,7)

    def test_real_ai_then_final_confirmation_through_inspection_and_fifo_usage(self):
        from forecasting.services.prediction_service import run_attendance_prediction
        prediction=run_attendance_prediction(self.plan.target_date,'dinner','참치볶음')
        self.plan.refresh_from_db();self.assertIsNone(self.plan.final_headcount)
        snapshot=self.ready(prediction.predicted_count)
        order=confirm_orders(snapshot.pk,self.operator)[0];item=order.items.get()
        inspect_item(item.pk,self.operator,item.required_qty,item.required_qty,'정상','5kg / 캔')
        self.client.post(reverse('meals:deduct_inventory'),{'target_date':str(self.plan.target_date),'meal_type':'석식','confirm':'1'})
        expected=item.required_qty-Decimal(prediction.predicted_count)/10
        self.assertEqual(current_stock(self.ing),expected)
        outgoing=InventoryLog.objects.get(log_type='출고')
        self.assertEqual(outgoing.lot_allocations.get().quantity,Decimal(prediction.predicted_count)/10)

    def test_same_legacy_stock_form_request_is_not_double_counted(self):
        now=timezone.now();record_inventory(self.ing.pk,'입고',10,self.operator,uuid.uuid4(),now)
        data={'ingredient':self.ing.pk,'log_type':'출고','quantity':'2','request_key':str(uuid.uuid4())}
        self.client.post(reverse('inventory:inventory_log_create'),data)
        self.client.post(reverse('inventory:inventory_log_create'),data)
        self.assertEqual(current_stock(self.ing),8)
        self.assertEqual(InventoryLog.objects.filter(log_type='출고').count(),1)

    def test_two_suppliers_split_orders_and_sort_by_real_name(self):
        other=get_user_model().objects.create_user(username='a-vendor',name='하업체',role='SUPPLIER')
        ing=Ingredient.objects.create(name='쌀',unit='kg',unit_price=100,safe_stock_level=0,supplier=other)
        SupplySpecification.objects.create(ingredient=ing,supplier=other,label='1kg',base_quantity=1,base_unit='kg',order_unit='kg',unit_price=100)
        Recipe.objects.create(menu=self.menu,ingredient=ing,required_amount=100,unit='g')
        orders=confirm_orders(self.ready(350).pk,self.operator)
        self.assertEqual(len(orders),2)
        response=self.client.get(reverse('procurement:workflow_inspections'))
        text=response.content.decode();self.assertLess(text.index('가업체'),text.index('하업체'))

    def test_expired_receipt_blocks_planning_until_disposal(self):
        now=timezone.now()
        today=timezone.localdate(now)
        self.plan.target_date=today+timedelta(days=(4-today.weekday())%7)
        self.plan.save(update_fields=['target_date'])
        record_inventory(self.ing.pk,'입고',3,self.operator,uuid.uuid4(),now-timedelta(days=3),expiration=now.date()-timedelta(days=1))
        save_headcount(self.plan.pk,350,350)
        with self.assertRaises(ValidationError):create_plan(self.plan.target_date,self.plan.target_date,self.operator,uuid.uuid4())

    def test_daily_edit_preserves_plan_identity_and_forecast(self):
        from forecasting.models import MealForecast
        forecast=MealForecast.objects.create(diet_plan=self.plan,predicted_count=100)
        response=self.client.post(reverse('meals:mealplan_create'),{'meal_date':str(self.plan.target_date),'dinner_menu':[str(self.menu.pk)]})
        self.assertEqual(response.status_code,302)
        self.assertTrue(DietPlan.objects.filter(pk=self.plan.pk).exists())
        self.assertTrue(MealForecast.objects.filter(pk=forecast.pk,diet_plan_id=self.plan.pk).exists())

    def test_inspection_document_date_supplier_filter_and_empty_state(self):
        order=self.order()
        response=self.client.get(reverse('procurement:workflow_inspections'),{'date':str(self.plan.target_date),'supplier':self.vendor.pk})
        self.assertContains(response,'참치')
        response=self.client.get(reverse('procurement:workflow_inspections'),{'date':'2026-01-01'})
        self.assertContains(response,'검수 대상이 없습니다.')

    def test_legacy_requirement_screen_uses_final_and_all_stock_types(self):
        from forecasting.services.ingredient_calc import get_all_day_requirements
        save_headcount(self.plan.pk,10,20)
        InventoryLog.objects.create(ingredient=self.ing,log_type='입고',quantity=5)
        InventoryLog.objects.create(ingredient=self.ing,log_type='폐기',quantity=1)
        InventoryLog.objects.create(ingredient=self.ing,log_type='조정',quantity=-1)
        result=get_all_day_requirements(self.plan.target_date)
        self.assertEqual(result['items']['참치']['total_needed'],2)
        self.assertEqual(result['items']['참치']['current_stock'],3)
        self.assertEqual(result['items']['참치']['order_amount'],0)

    def test_recipe_api_preserves_inventory_unit_and_rejects_nonpositive_amounts(self):
        from .test_workflows import workbook_file
        file=workbook_file([['메뉴명','식재료명','사용량','단위'],['참치볶음','참치',70,'g'],['오류메뉴','참치',-1,'g']])
        response=self.client.post(reverse('meals:recipe_upload_api'),{'excel_file':file})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['skipped_count'],1)
        self.recipe.refresh_from_db();self.ing.refresh_from_db()
        self.assertEqual((self.recipe.unit,self.recipe.required_amount,self.ing.unit),('g',70,'kg'))

    def test_bulk_upload_clears_old_confirmation(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        save_headcount(self.plan.pk,100,100)
        file=SimpleUploadedFile('meal.csv','date,meal_type,menu_name,headcount\n2026-10-16,석식,참치볶음,20\n'.encode())
        self.client.post(reverse('meals:mealplan_bulk_upload'),{'mealplan_file':file})
        self.plan.refresh_from_db();self.assertIsNone(self.plan.final_headcount)

    def test_legacy_simple_order_uses_idempotent_validated_snapshot(self):
        data={'ingredient_id[]':[str(self.ing.pk)],'quantity[]':['35.1'],'target_date':str(self.plan.target_date),'request_key':str(uuid.uuid4())}
        self.client.post(reverse('procurement:order_create'),data)
        self.client.post(reverse('procurement:order_create'),data)
        self.assertEqual(ProcurementPlan.objects.count(),1)
        self.assertFalse(PurchaseOrder.objects.exists())
        plan=ProcurementPlan.objects.get()
        self.assertEqual(plan.lines.get().package_quantity,8)
        self.assertEqual(confirm_orders(plan.pk,self.operator)[0].supplier,self.vendor)

    def test_legacy_smart_post_requires_final_and_creates_reviewable_snapshot(self):
        data={'order_start_date':str(self.plan.target_date),'order_end_date':str(self.plan.target_date),'request_key':str(uuid.uuid4())}
        response=self.client.post(reverse('procurement:order_from_mealplan'),data)
        self.assertEqual(response.status_code,302);self.assertFalse(ProcurementPlan.objects.exists())
        save_headcount(self.plan.pk,350,350)
        self.client.post(reverse('procurement:order_from_mealplan'),data)
        self.assertEqual(ProcurementPlan.objects.count(),1)
        self.assertFalse(PurchaseOrder.objects.exists())

    def test_new_ingredient_form_accepts_managed_category(self):
        IngredientCategory.objects.create(name='새분류')
        response=self.client.post(reverse('inventory:ingredient_create'),{'category':'새분류','name':'새재료','unit':'kg','unit_price':100,'safe_stock_level':1,'supplier':self.vendor.pk})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Ingredient.objects.get(name='새재료').category,'새분류')

    def test_kg_orders_follow_explicit_fractional_increment(self):
        self.spec.base_quantity=1;self.spec.order_unit='kg';self.spec.order_increment=Decimal('.01');self.spec.save()
        snapshot=self.ready(351);line=snapshot.lines.get()
        self.assertEqual(line.package_quantity,Decimal('35.10'))
        order=confirm_orders(snapshot.pk,self.operator,{str(line.pk):'35.11'})[0]
        self.assertEqual(order.items.get().required_qty,Decimal('35.11'))

    def test_daily_edit_empty_selection_removes_menus_without_deleting_plan(self):
        response=self.client.post(reverse('meals:mealplan_create'),{'meal_date':str(self.plan.target_date)})
        self.assertEqual(response.status_code,302)
        self.assertTrue(DietPlan.objects.filter(pk=self.plan.pk).exists())
        self.assertFalse(DietMenu.objects.filter(diet_plan=self.plan).exists())
        self.assertEqual(self.client.get(reverse('meals:mealplan_create'),{'date':'invalid'}).status_code,302)

    def test_recipe_api_returns_recipe_unit_instead_of_inventory_unit(self):
        response=self.client.get(reverse('meals:get_menu_recipes_api',args=[self.menu.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['recipes'][0]['unit'],'g')

    def test_purchase_requisition_prints_category_once_per_group(self):
        self.ing.category='분류중복검증';self.ing.save()
        self.order()
        response=self.client.get(reverse('procurement:doc_purchase_requisition'),{'start_date':str(self.plan.target_date),'end_date':str(self.plan.target_date)})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.content.decode().count('분류중복검증'),1)

    def test_order_preview_notes_persist_and_blank_print_does_not_change_final(self):
        snapshot=self.ready(350)
        response=self.client.post(reverse('procurement:workflow_plan',args=[snapshot.pk]),{'note_0':'선입고 확인'})
        self.assertEqual(response.status_code,302);snapshot.refresh_from_db()
        self.assertEqual(snapshot.details[0]['notes'],'선입고 확인')
        response=self.client.get(reverse('procurement:workflow_plan',args=[snapshot.pk]),{'blank':'1'})
        self.assertTrue(response.context['blank_inputs'])
        self.plan.refresh_from_db();self.assertEqual(self.plan.final_headcount,350)

    def test_issued_order_preview_shows_actual_adjusted_quantity(self):
        snapshot=self.ready(351);line=snapshot.lines.get()
        confirm_orders(snapshot.pk,self.operator,{str(line.pk):'9'})
        response=self.client.get(reverse('procurement:workflow_plan',args=[snapshot.pk]))
        self.assertEqual(response.context['lines'][0].confirmed_quantity,9)
        self.assertContains(response,'구매발주서 발행 완료')
