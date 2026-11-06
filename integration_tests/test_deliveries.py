"""Phase 2-A: actual repeated receipt workflow; all data is synthetic."""
import uuid
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, Client
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from accounts.access_service import set_roles
from inventory.models import Ingredient, InventoryLog, StockLot
from procurement.models import (Supplier, SupplierMembership, PurchaseOrder, OrderItem,
    SupplierFulfillment, DeliveryBatch, DeliveryReceipt, GoodsInspection)
from procurement.deliveries import schedule, inspect, progress
from procurement.workflow import current_stock, inspect_item


class RepeatedDeliveries(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user('round-buyer', role='NUTRITIONIST')
        self.vendor = User.objects.create_user('round-a', role='SUPPLIER', rbac_managed=True, account_state='ACTIVE')
        self.other = User.objects.create_user('round-b', role='SUPPLIER', rbac_managed=True, account_state='ACTIVE')
        for user in (self.vendor, self.other):
            set_roles(user, {'SUPPLIER'})
            company = Supplier.objects.create(user=user, name=user.username, category='농산물')
            SupplierMembership.objects.create(account=user, supplier=company, status='VERIFIED')
        self.ing = Ingredient.objects.create(name='합성 감자', unit='kg', safe_stock_level=0)
        self.order = PurchaseOrder.objects.create(supplier=self.vendor, status='승인')
        self.item = OrderItem.objects.create(purchase_order=self.order, ingredient=self.ing,
            required_qty=100, missing_qty=100, package_quantity=20, order_unit='통', spec_snapshot='5kg/통', order_unit_price=1000, estimated_price=100000)
        SupplierFulfillment.objects.create(order=self.order, state='ACCEPTED')
        self.today = timezone.localdate()

    def batch(self, quantity=60, **kwargs):
        data = dict(request_key=uuid.uuid4(), expected_date=self.today,
                    quantities={str(self.item.pk): quantity}, contact='합성 담당자')
        data.update(kwargs)
        return schedule(self.vendor, self.order.pk, **data)

    def receipt(self, batch, delivered=60, accepted=55, **kwargs):
        data = dict(delivered=delivered, accepted=accepted, actual_date=self.today,
                    specification='5kg/통', notes='불합격 또는 수량 차이')
        data.update(kwargs)
        return inspect(self.buyer, batch.lines.get().pk, **data)

    def test_100kg_60_then40_then5_rejected_redelivery(self):
        first = self.batch()
        self.assertEqual(current_stock(self.ing), 0)
        self.receipt(first)
        self.assertEqual(current_stock(self.ing), 55)
        self.assertEqual(progress(self.item)['rejected'], 5)
        self.order.refresh_from_db(); self.assertEqual(self.order.status, '승인')
        self.receipt(self.batch(40), 40, 40)
        self.receipt(self.batch(5), 5, 5)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, '완료')
        self.assertEqual(progress(self.item)['accepted'], 100)
        self.assertEqual(progress(self.item)['delivered'], 105)
        self.assertEqual(progress(self.item)['remaining'], 0)
        self.assertEqual(current_stock(self.ing), 100)
        self.assertEqual(StockLot.objects.aggregate(q=Sum('remaining_quantity'))['q'], 100)
        self.assertEqual(InventoryLog.objects.count(), 3)
        self.assertEqual(GoodsInspection.objects.count(), 0)

    def test_schedule_idempotent_no_duplicate_round(self):
        key = uuid.uuid4()
        a = self.batch(request_key=key)
        self.assertEqual(self.batch(request_key=key).pk, a.pk)
        self.assertEqual(DeliveryBatch.objects.count(), 1)

    def test_key_conflicting_payload_rejected(self):
        key = uuid.uuid4(); self.batch(request_key=key)
        with self.assertRaises(ValidationError): self.batch(20, request_key=key)

    def test_inspection_idempotent_no_duplicate_incoming(self):
        b = self.batch(); a = self.receipt(b)
        self.assertEqual(self.receipt(b).pk, a.pk)
        self.assertEqual(InventoryLog.objects.count(), 1)

    def test_inspection_different_resubmit_preserves_original(self):
        b = self.batch(); self.receipt(b)
        with self.assertRaises(ValidationError): self.receipt(b, accepted=56)
        self.assertEqual(current_stock(self.ing), 55)

    def test_reservation_prevents_overcommit(self):
        self.batch(60)
        with self.assertRaises(ValidationError): self.batch(41)
        self.assertEqual(progress(self.item)['available'], 40)

    def test_rejected_quantity_available_for_new_delivery(self):
        self.receipt(self.batch(100), 100, 0)
        self.assertEqual(progress(self.item)['available'], 100)
        self.assertEqual(InventoryLog.objects.count(), 0)
        self.batch(100)

    def test_invalid_quantities_rejected(self):
        for value in ('-1', '0', 'NaN', 'Infinity', '0.0000001', '1000000000'):
            with self.subTest(value=value), self.assertRaises(ValidationError): self.batch(value)
        self.assertFalse(DeliveryBatch.objects.exists())

    def test_invalid_dates_and_contact_rejected(self):
        for values in ({'expected_date':'bad'}, {'expected_date':self.today-timedelta(days=1)}, {'contact':''}):
            with self.subTest(values=values), self.assertRaises(ValidationError): self.batch(**values)

    def test_acceptance_above_delivered_or_planned_rejected(self):
        b = self.batch()
        for delivered, accepted in ((60,61), (61,60), (-1,0), (60,'NaN')):
            with self.subTest(delivered=delivered), self.assertRaises(ValidationError): self.receipt(b, delivered, accepted)
        self.assertFalse(InventoryLog.objects.exists())

    def test_expired_goods_not_accepted(self):
        with self.assertRaises(ValidationError): self.receipt(self.batch(), expiration=self.today-timedelta(days=1))

    def test_difference_requires_reason(self):
        with self.assertRaises(ValidationError): self.receipt(self.batch(), notes='')

    def test_future_actual_date_rejected(self):
        with self.assertRaises(ValidationError): self.receipt(self.batch(), actual_date=self.today+timedelta(days=1))

    def test_unit_change_blocks_receipt(self):
        b = self.batch(); self.ing.unit='g'; self.ing.save()
        with self.assertRaises(ValidationError): self.receipt(b)
        self.assertFalse(InventoryLog.objects.exists())

    def test_supplier_cannot_inspect_even_with_sub_admin(self):
        b = self.batch(); set_roles(self.vendor, {'SUPPLIER','SUB_ADMIN'})
        with self.assertRaises(PermissionDenied):
            inspect(self.vendor, b.lines.get().pk, delivered=60, accepted=60, actual_date=self.today, specification='5kg/통')
        self.assertFalse(InventoryLog.objects.exists())

    def test_other_supplier_service_idor(self):
        with self.assertRaises(PurchaseOrder.DoesNotExist):
            schedule(self.other, self.order.pk, request_key=uuid.uuid4(), expected_date=self.today,
                     quantities={str(self.item.pk):1}, contact='타 업체')

    def test_unverified_supplier_cannot_schedule(self):
        SupplierMembership.objects.filter(account=self.vendor).update(status='PENDING')
        with self.assertRaises(PermissionDenied): self.batch()

    def test_nonaccepted_order_cannot_schedule(self):
        self.order.fulfillment.state='NEW'; self.order.fulfillment.save()
        with self.assertRaises(ValidationError): self.batch()

    def test_foreign_item_rejected(self):
        with self.assertRaises(ValidationError): self.batch(quantities={'999999':1})

    def test_legacy_inspection_after_schedule_blocked(self):
        self.batch()
        with self.assertRaises(ValidationError): inspect_item(self.item.pk, self.buyer,100,100,'정상','5kg/통')
        self.assertFalse(GoodsInspection.objects.exists())

    def test_legacy_data_not_reopened_or_recredited(self):
        old = inspect_item(self.item.pk,self.buyer,60,55,'이상','5kg/통','기존 단건 기록')
        with self.assertRaises(ValidationError): self.batch(45)
        self.assertEqual(progress(self.item)['accepted'],55)
        self.assertEqual(GoodsInspection.objects.get().pk,old.pk)
        self.assertEqual(current_stock(self.ing),55)
        self.assertEqual(InventoryLog.objects.count(),1)

    def test_closed_order_duplicate_receipt_still_idempotent(self):
        b=self.batch(100); a=self.receipt(b,100,100)
        self.assertEqual(self.receipt(b,100,100).pk,a.pk)
        with self.assertRaises(ValidationError): self.batch(1)

    def test_review_flag_blocks_receipt(self):
        b=self.batch(); self.order.needs_review=True; self.order.save()
        with self.assertRaises(ValidationError): self.receipt(b)

    def test_supplier_buyer_page_and_inspection_post_denied(self):
        self.client.force_login(self.vendor)
        url=reverse('procurement:delivery_order',args=[self.order.pk])
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{}).status_code,403)

    def test_viewer_read_only(self):
        viewer=get_user_model().objects.create_user('round-viewer',rbac_managed=True,account_state='ACTIVE')
        set_roles(viewer,{'VIEWER'}); self.client.force_login(viewer)
        url=reverse('procurement:delivery_order',args=[self.order.pk])
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertNotContains(self.client.get(url),'검수 확정 · 합격량 입고')
        self.assertEqual(self.client.post(url,{}).status_code,403)

    def test_web_supplier_create_buyer_inspect_and_reread(self):
        url=reverse('procurement:portal_deliveries',args=[self.order.pk])
        self.client.force_login(self.vendor)
        self.assertContains(self.client.get(url),'회차별 납품')
        response=self.client.post(url,{'request_key':uuid.uuid4(),'expected_date':str(self.today),
            'q_'+str(self.item.pk):60,'contact':'합성 담당자','notes':''})
        self.assertEqual(response.status_code,302)
        line=DeliveryBatch.objects.get().lines.get()
        self.client.force_login(self.buyer)
        url=reverse('procurement:delivery_order',args=[self.order.pk])
        self.assertContains(self.client.get(url),'검수 확정 · 합격량 입고')
        response=self.client.post(url,{'line':line.pk,'delivered':60,'accepted':55,'actual_date':str(self.today),'specification':'5kg/통','notes':'5kg 불합격'})
        self.assertEqual(response.status_code,302)
        self.assertContains(self.client.get(url),'검수 완료')
        self.assertEqual(current_stock(self.ing),55)

    def test_foreign_supplier_web_idor(self):
        self.client.force_login(self.other)
        url=reverse('procurement:portal_deliveries',args=[self.order.pk])
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.post(url,{}).status_code,404)

    def test_csrf_required(self):
        c=Client(enforce_csrf_checks=True); c.force_login(self.vendor)
        self.assertEqual(c.post(reverse('procurement:portal_deliveries',args=[self.order.pk]),{}).status_code,403)

    def test_settlement_includes_split_receipts_once(self):
        self.receipt(self.batch())
        self.receipt(self.batch(40),40,40)
        self.client.force_login(self.buyer)
        response=self.client.get(reverse('procurement:workflow_settlement'),{'month':self.today.strftime('%Y-%m')})
        self.assertEqual(response.status_code,200)
        row=response.context['rows'][0]
        self.assertEqual(row['inspected_amount'],Decimal('95000'))
        self.assertEqual(row['supplier'].pk,self.vendor.pk)

    def test_old_inspection_url_redirects_to_rounds(self):
        self.batch();self.client.force_login(self.buyer)
        self.assertRedirects(self.client.get(reverse('procurement:workflow_inspection',args=[self.item.pk])),reverse('procurement:delivery_order',args=[self.order.pk]))

    def test_zero_delivered_releases_reservation_without_stock(self):
        self.receipt(self.batch(),0,0)
        self.assertEqual(progress(self.item)['available'],100)
        self.assertFalse(InventoryLog.objects.exists())


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError


class DeliveryConcurrency(TransactionTestCase):
    setUp = RepeatedDeliveries.setUp
    batch = RepeatedDeliveries.batch
    receipt = RepeatedDeliveries.receipt

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
            jobs=[pool.submit(worker) for _ in range(2)]
            return [job.result(timeout=30) for job in jobs]

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_rounds_cannot_overreserve(self):
        def operation():
            try:
                return ('saved',self.batch(60).pk)
            except ValidationError:
                return ('rejected',None)
        result=self.race(operation)
        self.assertEqual(sorted(x[0] for x in result),['rejected','saved'])
        self.assertEqual(DeliveryBatch.objects.count(),1)
        self.assertEqual(progress(self.item)['reserved'],60)

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_receipt_credited_once(self):
        b=self.batch()
        result=self.race(lambda:self.receipt(b).pk)
        self.assertEqual(result[0],result[1])
        self.assertEqual(DeliveryReceipt.objects.count(),1)
        self.assertEqual(current_stock(self.ing),55)
        self.assertEqual(InventoryLog.objects.count(),1)

    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_identical_schedule_same_round(self):
        key=uuid.uuid4()
        result=self.race(lambda:self.batch(request_key=key).pk)
        self.assertEqual(result[0],result[1])
        self.assertEqual(DeliveryBatch.objects.count(),1)


class DeliveryMigrationPreservation(TransactionTestCase):
    def test_empty_additive_migration_roundtrip_preserves_legacy_receipt(self):
        RepeatedDeliveries.setUp(self)
        old=inspect_item(self.item.pk,self.buyer,100,100,'정상','5kg/통')
        log_id=old.inventory_log_id
        targets=MigrationExecutor(connection).loader.graph.leaf_nodes()
        executor=MigrationExecutor(connection)
        executor.migrate([('procurement','0012_suppliermembership_registered_via_portal')])
        try:
            old_apps=executor.loader.project_state([('procurement','0012_suppliermembership_registered_via_portal')]).apps
            self.assertEqual(old_apps.get_model('procurement','GoodsInspection').objects.get(pk=old.pk).inventory_log_id,log_id)
        finally:
            MigrationExecutor(connection).migrate(targets)
        self.assertEqual(GoodsInspection.objects.get(pk=old.pk).inventory_log_id,log_id)
        self.assertEqual(current_stock(self.ing),100)
        self.assertEqual(InventoryLog.objects.count(),1)
        self.assertEqual(get_user_model().objects.get(pk=self.buyer.pk).username,'round-buyer')
        self.assertEqual(PurchaseOrder.objects.get(pk=self.order.pk).status,'완료')
        self.assertFalse(DeliveryBatch.objects.exists())

    def test_rollback_refuses_to_drop_used_delivery_history(self):
        RepeatedDeliveries.setUp(self)
        batch=RepeatedDeliveries.batch(self)
        with self.assertRaises(IrreversibleError):
            MigrationExecutor(connection).migrate([('procurement','0012_suppliermembership_registered_via_portal')])
        self.assertTrue(DeliveryBatch.objects.filter(pk=batch.pk).exists())
