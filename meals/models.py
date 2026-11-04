from django.db import models
from inventory.models import Ingredient  # 식재료 모델 가져오기

# 3. Menu (메뉴)
class Menu(models.Model):
    name = models.CharField(max_length=100, verbose_name="메뉴명")
    # ✨ 살짝 추가: 메뉴의 카테고리 (예: 한식, 일식, 중식)
    category = models.CharField(max_length=50, blank=True, null=True, verbose_name="메뉴 분류")

    cooking_notes = models.TextField(blank=True, default="", verbose_name="조리 정보")

    def __str__(self):
        return self.name

# 4. Recipe (레시피 - 메뉴와 식재료 매핑)
class Recipe(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='recipes')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='used_in_recipes')
    unit = models.CharField(max_length=20, blank=True, default="", verbose_name="1인분 기준 단위")
    required_amount = models.DecimalField(max_digits=14, decimal_places=6, help_text="1인분 소요량 (예: 0.15)")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['menu', 'ingredient'], name='unique_recipe_ingredient')
        ]

    def __str__(self):
        return f"{self.menu.name} - {self.ingredient.name} ({self.required_amount})"

# 5. Diet_Plan (식단)
class DietPlan(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = '조식', '조식'
        LUNCH = '중식', '중식'
        DINNER = '석식', '석식'
        OTHER = '기타', '기타'

    target_date = models.DateField(verbose_name="식단 날짜")
    meal_type = models.CharField(max_length=10, choices=MealType.choices, verbose_name="끼니")
    headcount = models.IntegerField(default=0, verbose_name="식수(목표/당일인원)")
    final_headcount = models.PositiveIntegerField(null=True, blank=True, verbose_name="최종 확정 식수")
    headcount_confirmed_at = models.DateTimeField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False, verbose_name="식단 확정")
    is_served = models.BooleanField(default=False, verbose_name="재고 차감 완료 여부")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['target_date', 'meal_type'], name='unique_diet_plan')
        ]

    def __str__(self):
        return f"{self.target_date} {self.meal_type}"


# 6. Diet_Menu (식단 상세 - 한 끼니에 여러 메뉴 구성)
class DietMenu(models.Model):
    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name='diet_menus')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['diet_plan', 'menu'], name='unique_diet_menu')
        ]

    def __str__(self):
        return f"{self.diet_plan} -> {self.menu.name}"

class CookingInstruction(models.Model):
    diet_plan = models.OneToOneField(DietPlan, on_delete=models.CASCADE, related_name='cooking_instruction')
    instructions = models.TextField(blank=True, default='', verbose_name='현장 조리 지시·비고')
    inventory_instructions = models.TextField(blank=True, default='', verbose_name='재고 사용 지시')
    line_notes = models.JSONField(default=dict, blank=True, verbose_name='재료별 비고')
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
