"""Real row-lock races, run only on the task's isolated supporting database."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TransactionTestCase,skipUnlessDBFeature
from django.db import close_old_connections
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from inventory.models import Ingredient,SupplySpecification,InventoryLog,StockAllocation,StockLot
from procurement.models import GoodsInspection
from procurement.workflow import create_manual_plan,confirm_orders,inspect_item,record_inventory,current_stock


class ConcurrentInventoryContracts(TransactionTestCase):
    def setUp(self):
        U=get_user_model()
        self.user=U.objects.create_user(username='race-operator',name='경합 검증',is_staff=True)
        self.vendor=U.objects.create_user(username='race-vendor',name='경합 업체',role='SUPPLIER')
        self.ing=Ingredient.objects.create(name='경합 재료',unit='kg',unit_price=100,safe_stock_level=0,supplier=self.vendor)
        SupplySpecification.objects.create(ingredient=self.ing,supplier=self.vendor,label='1kg',base_quantity=1,base_unit='kg',order_unit='kg',unit_price=100)

    def race(self, operation):
        barrier=Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(worker) for _ in range(2)]
            return [future.result(timeout=30) for future in futures]

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_identical_inspection_only_receives_once(self):
        plan=create_manual_plan([(self.ing.pk,5)],timezone.localdate(),self.user,uuid.uuid4())
        item=confirm_orders(plan.pk,self.user)[0].items.get()
        results=self.race(lambda:inspect_item(item.pk,self.user,5,4,'이상','1kg','1kg 품질 반품').pk)
        self.assertEqual(results[0],results[1])
        self.assertEqual(GoodsInspection.objects.count(),1)
        self.assertEqual(InventoryLog.objects.filter(log_type='입고').count(),1)
        self.assertEqual(current_stock(self.ing),4)

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_outgoing_cannot_overspend_stock(self):
        record_inventory(self.ing.pk,'입고',10,self.user,uuid.uuid4(),timezone.now())
        def outgoing():
            try:
                return ('saved',record_inventory(self.ing.pk,'출고',6,self.user,uuid.uuid4(),timezone.now()).pk)
            except ValidationError:
                return ('shortage',None)
        results=self.race(outgoing)
        self.assertEqual(sorted(r[0] for r in results),['saved','shortage'])
        self.assertEqual(current_stock(self.ing),4)
        self.assertEqual(InventoryLog.objects.filter(log_type='출고').count(),1)
        self.assertEqual(StockAllocation.objects.get().quantity,6)
        self.assertEqual(StockLot.objects.get().remaining_quantity,4)
