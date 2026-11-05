from django.contrib import admin
from .models import Menu, Recipe, DietPlan, DietMenu
from django.core.exceptions import PermissionDenied


def served_menu(obj):
    return bool(obj and DietMenu.objects.filter(menu=obj, diet_plan__is_served=True).exists())

# 메뉴를 만들 때, 레시피(식재료)를 한 화면에서 바로 추가할 수 있게 해주는 마법!
class RecipeInline(admin.TabularInline):
    model = Recipe
    extra = 3  # 기본으로 빈칸 3개를 보여줍니다.
    
    # 🚀 핵심 마법: 250개 식재료를 스크롤로 찾지 않고, 돋보기 검색(자동완성)으로 찾게 해줍니다!
    autocomplete_fields = ['ingredient'] 

    def has_change_permission(self, request, obj=None):
        return not served_menu(obj) and super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        return not served_menu(obj) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not served_menu(obj) and super().has_delete_permission(request, obj)

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ['name']
    inlines = [RecipeInline]  # 메뉴 화면 안에 레시피 화면을 쏙 집어넣습니다.

    def has_view_permission(self, request, obj=None):
        # A served menu is available through the business read-only screens.
        return not served_menu(obj) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return not served_menu(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not served_menu(obj) and super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        from .change_policy import guard_menu_change, mark_menu_change
        if change:
            guard_menu_change([obj.pk])
        super().save_model(request, obj, form, change)
        mark_menu_change([obj.pk])

    def delete_queryset(self, request, queryset):
        if DietMenu.objects.filter(menu__in=queryset, diet_plan__is_served=True).exists():
            raise PermissionDenied('사용 완료된 메뉴는 삭제할 수 없습니다.')
        from .change_policy import mark_menu_change
        mark_menu_change(list(queryset.values_list('pk', flat=True)))
        super().delete_queryset(request, queryset)

# 식단표 관련 등록
class DietMenuInline(admin.TabularInline):
    model = DietMenu
    extra = 2
    autocomplete_fields = ['menu']

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_served) and super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        return not (obj and obj.is_served) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_served) and super().has_delete_permission(request, obj)

@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('target_date', 'meal_type')
    list_filter = ('target_date', 'meal_type')
    inlines = [DietMenuInline]

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_served) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj:
            from .change_policy import guard_plan_delete
            from django.core.exceptions import ValidationError
            try:
                guard_plan_delete(DietPlan.objects.filter(pk=obj.pk))
            except ValidationError:
                return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        from procurement.workflow import invalidate_plans
        super().save_model(request, obj, form, change)
        invalidate_plans([obj.pk])

    def delete_queryset(self, request, queryset):
        from .change_policy import guard_plan_delete
        guard_plan_delete(queryset)
        super().delete_queryset(request, queryset)
