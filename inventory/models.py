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
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    transaction_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='변동 사유')

    def __str__(self):
        return f"{self.ingredient.name} - {self.log_type}({self.quantity})"

class IngredientCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class SupplySpecification(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="supply_specs")
    supplier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    label = models.CharField(max_length=100, help_text="예: 700g(70g×10개), 브랜드 포함")
    base_quantity = models.DecimalField(max_digits=14, decimal_places=6)
    base_unit = models.CharField(max_length=20)
    order_unit = models.CharField(max_length=20, help_text="예: 캔, 봉, 개, kg")
    order_increment = models.DecimalField(max_digits=14, decimal_places=6, default=1, help_text="발주 간격: 캔은 1, kg 소수 발주는 0.01 등 명시")
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, help_text="발주 단위당 가격")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["ingredient", "supplier"], name="unique_supply_spec")]

    def __str__(self):
        return f"{self.ingredient.name} / {self.supplier.name} / {self.label}"


class StockLot(models.Model):
    incoming_log = models.OneToOneField(InventoryLog, on_delete=models.PROTECT, related_name='stock_lot')
    remaining_quantity = models.DecimalField(max_digits=18, decimal_places=6)


class StockAllocation(models.Model):
    outgoing_log = models.ForeignKey(InventoryLog, on_delete=models.PROTECT, related_name='lot_allocations')
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, related_name='allocations')
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
