from django.contrib import admin
from .models import Ingredient, InventoryLog

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'unit_price', 'safe_stock_level', 'supplier')
    search_fields = ['name'] # 이름으로 검색할 수 있게 허용!
    list_display = ('name', 'spec', 'category', 'unit_price') # (보너스) 목록에서 예쁘게 보이게 하기
@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'log_type', 'quantity', 'transaction_date')
