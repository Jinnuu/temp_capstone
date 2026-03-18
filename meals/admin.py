from django.contrib import admin
from .models import Menu, Recipe, DietPlan, DietMenu

# 메뉴 화면 안에 레시피 입력칸을 표(Table) 형태로 집어넣기
class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 1  # 기본 빈 칸 1개 표시

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    inlines = [RecipeInline]

# 식단 화면 안에 메뉴 입력칸 집어넣기
class DietMenuInline(admin.TabularInline):
    model = DietMenu
    extra = 1

@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('target_date', 'meal_type')
    inlines = [DietMenuInline]
