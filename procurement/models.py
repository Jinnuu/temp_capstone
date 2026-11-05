import uuid
from django.db import models
from django.conf import settings
from inventory.models import Ingredient

# 8. Supplier (발주 업체 / 거래처 관리)
class Supplier(models.Model):
    category = models.CharField(max_length=50, verbose_name="구분", help_text="예: 부식업체, 농산물, 육류 등")
    name = models.CharField(max_length=100, verbose_name="상호명")
    business_items = models.CharField(max_length=200, blank=True, null=True, verbose_name="거래품목", help_text="예: 곡류, 농산물 등")
    phone_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="전화번호")
    fax = models.CharField(max_length=30, blank=True, null=True, verbose_name="팩스")
    mobile = models.CharField(max_length=30, blank=True, null=True, verbose_name="핸드폰")
    remarks = models.TextField(blank=True, null=True, verbose_name="비고(이메일)")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_profile',
        verbose_name="연동 계정"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "거래처(공급업체)"
        verbose_name_plural = "거래처(공급업체) 목록"
        ordering = ["name"]

    def __str__(self):
        return f"[{self.category or '공급업체'}] {self.name}"

# 9. Purchase_Order (발주서 메인)
class PurchaseOrder(models.Model):

    class Status(models.TextChoices):
        PENDING = '대기', '대기'
        APPROVED = '승인', '승인'
        DELIVERED = '완료', '완료'

    workflow_plan = models.ForeignKey("ProcurementPlan", null=True, blank=True, on_delete=models.PROTECT, related_name="orders")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    needs_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # 업체(User) 연결
    supplier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchase_orders')
    total_amount = models.IntegerField(default=0)

    def __str__(self):
        return f"발주서 #{self.id} - {self.supplier.name or self.supplier.username} ({self.status})"

# 10. Order_Item (발주서 상세 품목)
class OrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    package_quantity = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    order_unit = models.CharField(max_length=20, blank=True, default="")
    spec_snapshot = models.CharField(max_length=200, blank=True, default="")
    target_date = models.DateField(null=True, blank=True, verbose_name="요청일(식단일)")
    meal_type = models.CharField(max_length=10, null=True, blank=True, verbose_name="끼니 구문")
    required_qty = models.DecimalField(max_digits=18, decimal_places=6)
    missing_qty = models.DecimalField(max_digits=18, decimal_places=6)
    order_unit_price = models.IntegerField(help_text="발주 생성 시점의 과거 단가 스냅샷")
    estimated_price = models.IntegerField()

    @property
    def purchase_quantity(self):
        return self.package_quantity if self.package_quantity is not None else self.missing_qty

    @property
    def purchase_unit(self):
        return self.order_unit if self.package_quantity is not None else self.ingredient.unit

    @property
    def purchase_spec(self):
        return self.spec_snapshot if self.package_quantity is not None else self.ingredient.spec

    @property
    def purchase_price(self):
        if self.package_quantity is not None and self.purchase_order.workflow_plan_id:
            line = self.purchase_order.workflow_plan.lines.filter(ingredient_id=self.ingredient_id, order_date=self.target_date).first()
            if line:
                return line.unit_price
        return self.order_unit_price

    class Meta:
        # SQL: UNIQUE(order_id, ingredient_id, target_date, meal_type) 반영
        constraints = [
            models.UniqueConstraint(fields=['purchase_order', 'ingredient', 'target_date', 'meal_type'], name='unique_order_ingredient_date_meal')
        ]

    def __str__(self):
        return f"[{self.purchase_order.id}] {self.ingredient.name}"


class ProcurementPlan(models.Model):
    request_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    start_date = models.DateField()
    end_date = models.DateField()
    meal_ids = models.JSONField(default=list)
    details = models.JSONField(default=list)
    source_fingerprint = models.CharField(max_length=64)
    needs_review = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="draft")


class ProcurementPlanLine(models.Model):
    plan = models.ForeignKey(ProcurementPlan, on_delete=models.CASCADE, related_name="lines")
    order_date = models.DateField()
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)
    supplier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    needed_qty = models.DecimalField(max_digits=18, decimal_places=6)
    stock_before = models.DecimalField(max_digits=18, decimal_places=6)
    safe_stock = models.DecimalField(max_digits=18, decimal_places=6)
    shortage_qty = models.DecimalField(max_digits=18, decimal_places=6)
    package_size = models.DecimalField(max_digits=18, decimal_places=6)
    order_increment = models.DecimalField(max_digits=14, decimal_places=6, default=1)
    package_quantity = models.DecimalField(max_digits=14, decimal_places=6)
    order_unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    spec_snapshot = models.CharField(max_length=200)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["plan", "order_date", "ingredient"], name="unique_plan_date_ingredient")]


class GoodsInspection(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="inspection")
    inspected_at = models.DateTimeField(auto_now_add=True)
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    delivered_qty = models.DecimalField(max_digits=18, decimal_places=6)
    accepted_qty = models.DecimalField(max_digits=18, decimal_places=6)
    condition = models.CharField(max_length=20, choices=[("정상", "정상"), ("이상", "이상"), ("반품", "반품")])
    specification = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    inventory_log = models.OneToOneField("inventory.InventoryLog", null=True, blank=True, on_delete=models.PROTECT)


class InventoryTransactionKey(models.Model):
    request_key = models.UUIDField(unique=True)
    inventory_log = models.OneToOneField("inventory.InventoryLog", on_delete=models.PROTECT)


class SupplierMembership(models.Model):
    """Verified portal membership; never rewrites legacy order ownership."""
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='portal_membership')
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name='memberships')
    registered_via_portal = models.BooleanField(default=False)
    requested_company = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=50)
    contact_phone = models.CharField(max_length=30)
    status = models.CharField(max_length=12, choices=[('PENDING','소속 확인 대기'),('VERIFIED','확인 완료'),('REJECTED','확인 거절')], default='PENDING')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_supplier_memberships')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)
    revision = models.PositiveIntegerField(default=0)


class SupplierFulfillment(models.Model):
    order = models.OneToOneField(PurchaseOrder, on_delete=models.PROTECT, related_name='fulfillment')
    state = models.CharField(max_length=20, choices=[('NEW','신규'),('ACKNOWLEDGED','접수 확인'),('ACCEPTED','수락'),('REJECTED','거절'),('PREPARING','출고 준비'),('DISPATCHED','출고 완료')], default='NEW')
    delivery_date = models.DateField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    notes = models.CharField(max_length=1000, blank=True)
    revision = models.PositiveIntegerField(default=0)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)


class SupplierDeliveryLine(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name='delivery_plan')
    planned_quantity = models.DecimalField(max_digits=18, decimal_places=6)
