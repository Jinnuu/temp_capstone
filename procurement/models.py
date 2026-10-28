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
    target_date = models.DateField(null=True, blank=True, verbose_name="요청일(식단일)")
    meal_type = models.CharField(max_length=10, null=True, blank=True, verbose_name="끼니 구문")
    required_qty = models.DecimalField(max_digits=10, decimal_places=2)
    missing_qty = models.DecimalField(max_digits=10, decimal_places=2)
    order_unit_price = models.IntegerField(help_text="발주 생성 시점의 과거 단가 스냅샷")
    estimated_price = models.IntegerField()

    class Meta:
        # SQL: UNIQUE(order_id, ingredient_id, target_date, meal_type) 반영
        constraints = [
            models.UniqueConstraint(fields=['purchase_order', 'ingredient', 'target_date', 'meal_type'], name='unique_order_ingredient_date_meal')
        ]

    def __str__(self):
        return f"[{self.purchase_order.id}] {self.ingredient.name}"
