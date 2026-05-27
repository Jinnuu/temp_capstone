from django.db import models
from django.conf import settings
from django.utils import timezone

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    spec = models.CharField(max_length=100, null=True, blank=True, verbose_name='규격')
    description = models.TextField(null=True, blank=True, verbose_name='식품 설명')
    unit = models.CharField(max_length=20, help_text="예: kg, g, EA")
    unit_price = models.IntegerField(default=0)
    safe_stock_level = models.DecimalField(max_digits=10, decimal_places=2)
    # SQL: FOREIGN KEY (supplier_id) REFERENCES User(user_id) 
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='supplied_ingredients'
    )
    
    # ✨ 새롭게 추가된 엑셀 데이터 3줄 (여기에 쏙 들어갑니다!)
    category = models.CharField(max_length=50, null=True, blank=True, verbose_name='대분류')
    yearly_demand = models.IntegerField(null=True, blank=True, verbose_name='연간예상소요량')
    total_amount = models.IntegerField(null=True, blank=True, verbose_name='금액')

    # 재고 수불 연동용 필드
    #current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name='현재 재고량')

    def __str__(self):
        return self.name

class InventoryLog(models.Model):
    class LogType(models.TextChoices):
        IN = '입고', '입고'
        OUT = '출고', '출고'
        WASTE = '폐기', '폐기'
        ADJ = '조정', '조정'

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    log_type = models.CharField(max_length=10, choices=LogType.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='변동 사유')

    def __str__(self):
        return f"{self.ingredient.name} - {self.log_type}({self.quantity})"