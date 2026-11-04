"""Read-only assertions against only this task's disposable SQLite application."""
import os,json
from decimal import Decimal
os.environ['DJANGO_SETTINGS_MODULE']='config.test_settings'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['NAME']=='/tmp/sprint7-integration.sqlite3'
from inventory.models import Ingredient,InventoryLog,StockLot,StockAllocation
from meals.models import DietPlan,Recipe,Menu,CookingInstruction
from forecasting.models import AttendancePrediction
from procurement.models import PurchaseOrder,OrderItem,GoodsInspection
from procurement.workflow import current_stock
import openpyxl
from pathlib import Path
root=Path('/workspace/verification/comprehensive-20261104')
tuna=Ingredient.objects.get(name='QA 참치');tofu=Ingredient.objects.get(name='QA 두부')
assert (current_stock(tuna),current_stock(tofu))==(Decimal('5.9'),Decimal('.9'))
assert (PurchaseOrder.objects.count(),OrderItem.objects.count(),GoodsInspection.objects.count(),InventoryLog.objects.count())==(2,2,2,6)
assert list(Recipe.objects.filter(menu__name='QA 통합 메뉴').values_list('required_amount','unit'))==[(Decimal('100'),'g')]*2
plan=DietPlan.objects.get(target_date='2026-11-06',meal_type='석식')
assert (plan.headcount,plan.final_headcount,plan.is_served)==(360,351,True)
assert DietPlan.objects.get(target_date='2026-11-10',meal_type='조식').headcount==77
assert Recipe.objects.filter(menu__name='QA 업로드 메뉴',ingredient=tuna,required_amount=100,unit='g').exists()
assert not Menu.objects.filter(name='QA 삭제 메뉴').exists()
assert CookingInstruction.objects.get(diet_plan=plan).instructions=='QA 조리 중심 온도 확인'
predictions=AttendancePrediction.objects.filter(prediction_date='2026-11-06')
assert predictions.count()==3
assert all(p.predicted_count>=0 and p.input_features.get('feature_columns') for p in predictions)
lots=list(StockLot.objects.filter(incoming_log__ingredient=tuna).order_by('incoming_log__transaction_date','id'))
assert [lot.remaining_quantity for lot in lots]==[Decimal('3.9'),Decimal('2')]
assert StockAllocation.objects.filter(outgoing_log__ingredient=tuna).count()==2
assert sum(PurchaseOrder.objects.values_list('total_amount',flat=True))==11700
accepted=sum(Decimal(x.order_item.estimated_price)*x.accepted_qty/x.order_item.required_qty for x in GoodsInspection.objects.select_related('order_item'))
assert accepted==11200
vendor=openpyxl.load_workbook(root/'vendor-order.xlsx')
rows=list(vendor.active.values);assert len(rows)==3
by_name={row[4]:row for row in rows[1:]}
assert (by_name['QA 참치'][6],by_name['QA 참치'][7],by_name['QA 참치'][9],by_name['QA 참치'][10])==('캔',500,9,4500)
assert (by_name['QA 두부'][6],by_name['QA 두부'][7],by_name['QA 두부'][9],by_name['QA 두부'][10])==('판',600,12,7200)
cooking=openpyxl.load_workbook(root/'cooking.xlsx')
assert cooking['계산근거']['G2'].value==35.1 and cooking['계산근거']['G3'].value==35.1
assert all(cell.data_type!='f' for book in [vendor,cooking] for sheet in book for row in sheet for cell in row)
print(json.dumps({'passed':True,'stock':{'tuna':'5.9kg','tofu':'0.9kg'},'orders':2,'items':2,'inspections':2,'inventory_logs':6,'ordered_amount':11700,'accepted_value':11200,'tuna_lot_remainders':['3.9','2'],'predictions':list(predictions.values('meal_type','predicted_count','model_name')),'excel_snapshot_values':True,'recipe_upload_and_mealplan_upload_persisted':True,'no_inventory_change_from_cooking':True},ensure_ascii=False,indent=2))
