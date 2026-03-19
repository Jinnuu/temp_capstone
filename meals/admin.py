from django.contrib import admin
from .models import Menu, Recipe, DietPlan, DietMenu

# 메뉴를 만들 때, 레시피(식재료)를 한 화면에서 바로 추가할 수 있게 해주는 마법!
class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 3  # 기본으로 빈칸 3개를 보여줍니다.
    
    # 🚀 핵심 마법: 250개 식재료를 스크롤로 찾지 않고, 돋보기 검색(자동완성)으로 찾게 해줍니다!
    autocomplete_fields = ['ingredient'] 

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ['name']
    inlines = [RecipeInline]  # 메뉴 화면 안에 레시피 화면을 쏙 집어넣습니다.

# 식단표 관련 등록
class DietMenuInline(admin.TabularInline):
    model = DietMenu
    extra = 2
    autocomplete_fields = ['menu']

@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('target_date', 'meal_type')
    list_filter = ('target_date', 'meal_type')
    inlines = [DietMenuInline]