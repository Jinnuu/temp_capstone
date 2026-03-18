from django.db import models
from meals.models import DietPlan

# 8. Meal_Forecast (식수 예측 및 결과)
class MealForecast(models.Model):
    # SQL: UNIQUE + FOREIGN KEY -> OneToOneField 사용
    diet_plan = models.OneToOneField(DietPlan, on_delete=models.CASCADE, related_name='forecast')
    predicted_count = models.IntegerField()
    reference_data = models.JSONField(null=True, blank=True)
    actual_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.diet_plan} 예측: {self.predicted_count}명"