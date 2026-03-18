from django.contrib import admin
from .models import Ingredient, InventoryLog

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'unit_price', 'safe_stock_level', 'supplier')

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'log_type', 'quantity', 'transaction_date')