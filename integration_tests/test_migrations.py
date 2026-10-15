from datetime import datetime, timezone
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ExistingDataMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_inventory_logs_users_orders_and_items(self):
        old_targets=[('inventory','0006_ingredient_description'),('procurement','0004_remove_orderitem_unique_order_ingredient_date_and_more')]
        latest=MigrationExecutor(connection).loader.graph.leaf_nodes()
        executor=MigrationExecutor(connection)
        executor.migrate(old_targets)
        try:
            apps=executor.loader.project_state(old_targets).apps
            user=apps.get_model('accounts','User').objects.create(username='historical-supplier',name='기존업체',password='unused')
            ingredient=apps.get_model('inventory','Ingredient').objects.create(name='기존재료',unit='kg',unit_price=100,safe_stock_level=2,supplier=user)
            log=apps.get_model('inventory','InventoryLog').objects.create(ingredient=ingredient,log_type='입고',quantity=Decimal('7.25'),description='보존해야 할 이력')
            order=apps.get_model('procurement','PurchaseOrder').objects.create(supplier=user,status='배송완료',total_amount=725)
            item=apps.get_model('procurement','OrderItem').objects.create(purchase_order=order,ingredient=ingredient,required_qty=Decimal('7.25'),missing_qty=Decimal('7.25'),order_unit_price=100,estimated_price=725)
            saved_time=log.transaction_date
            MigrationExecutor(connection).migrate(latest)
            from inventory.models import InventoryLog, Ingredient
            from procurement.models import PurchaseOrder, OrderItem
            from django.contrib.auth import get_user_model
            self.assertEqual(InventoryLog.objects.get(pk=log.pk).transaction_date,saved_time)
            self.assertEqual(InventoryLog.objects.get(pk=log.pk).quantity,Decimal('7.25'))
            self.assertEqual(Ingredient.objects.get(pk=ingredient.pk).supplier_id,user.pk)
            self.assertEqual(PurchaseOrder.objects.get(pk=order.pk).status,'배송완료')
            self.assertEqual(OrderItem.objects.get(pk=item.pk).estimated_price,725)
            self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
