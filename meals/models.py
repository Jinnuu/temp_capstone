from django.db import models
from inventory.models import Ingredient  # inventory 앱의 식재료 모델 가져오기

# 3. Menu (메뉴)
class Menu(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# 4. Recipe (레시피 - 메뉴와 식재료 매핑)
class Recipe(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='recipes')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='used_in_recipes')
    required_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="1인분 소요량")

    class Meta:
        # SQL: UNIQUE(menu_id, ingredient_id) 반영
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

    target_date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.choices)

    class Meta:
        # SQL: UNIQUE(target_date, meal_type) 반영
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
        # SQL: UNIQUE(diet_id, menu_id) 반영
        constraints = [
            models.UniqueConstraint(fields=['diet_plan', 'menu'], name='unique_diet_menu')
        ]

    def __str__(self):
        return f"{self.diet_plan} -> {self.menu.name}"