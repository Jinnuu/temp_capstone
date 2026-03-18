from django.db import models
from django.conf import settings

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
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

    def __str__(self):
        return self.name

class InventoryLog(models.Model):
    class LogType(models.TextChoices):
        IN = '입고', '입고'
        OUT = '출고', '출고'
        WASTE = '폐기', '폐기'

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    log_type = models.CharField(max_length=10, choices=LogType.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.ingredient.name} - {self.log_type}({self.quantity})"