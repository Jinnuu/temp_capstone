from django.contrib import admin
from .models import Ingredient, StockTransaction


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "unit_price")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "ingredient", "transaction_type", "quantity", "created_at")
