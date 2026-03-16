from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="ea")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("IN", "In"),
        ("OUT", "Out"),
        ("ADJUST", "Adjust"),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    memo = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.ingredient.name} - {self.transaction_type} - {self.quantity}"
