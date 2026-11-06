import django,json
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
assert settings.DATABASES['default']['NAME']=='snp_auth_verification'
from procurement.models import PurchaseOrder,DeliveryReceipt,GoodsInspection
from procurement.deliveries import progress
from procurement.workflow import current_stock
from inventory.models import InventoryLog,StockLot
from django.db.models import Sum
order=PurchaseOrder.objects.get(supplier__username='phase2-browser-a')
item=order.items.get()
result={'order_status':order.status,'progress':{k:str(v) for k,v in progress(item).items()},
        'stock':str(current_stock(item.ingredient)),
        'incoming_log_count':InventoryLog.objects.filter(ingredient=item.ingredient,log_type='입고').count(),
        'lot_remaining':str(StockLot.objects.filter(incoming_log__ingredient=item.ingredient).aggregate(q=Sum('remaining_quantity'))['q']),
        'legacy_inspection_count':GoodsInspection.objects.count(),'receipt_count':DeliveryReceipt.objects.count()}
assert order.status=='완료'
assert current_stock(item.ingredient)==100
assert result['incoming_log_count']==3
assert result['receipt_count']==3
assert result['legacy_inspection_count']==0
for receipt in DeliveryReceipt.objects.select_related('inventory_log'):
    assert receipt.inventory_log.quantity==receipt.accepted_quantity
print(json.dumps(result,indent=2,ensure_ascii=False))
