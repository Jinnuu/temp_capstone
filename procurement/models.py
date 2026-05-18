from django.db import models
from django.conf import settings
from inventory.models import Ingredient

# 9. Purchase_Order (발주서 메인)
class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = '대기', '대기'
        APPROVED = '승인', '승인'
        SHIPPING = '배송중', '배송중'
        DELIVERED = '배송완료', '배송완료'

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
    menu_name = models.CharField(max_length=200, null=True, blank=True, verbose_name="메뉴명")
    required_qty = models.DecimalField(max_digits=10, decimal_places=2)
    missing_qty = models.DecimalField(max_digits=10, decimal_places=2)
    order_unit_price = models.IntegerField(help_text="발주 생성 시점의 과거 단가 스냅샷")
    estimated_price = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['purchase_order', 'ingredient', 'target_date', 'meal_type', 'menu_name'], name='unique_order_ingredient_date_meal_menu')
        ]

    def __str__(self):
        return f"[{self.purchase_order.id}] {self.ingredient.name}"
