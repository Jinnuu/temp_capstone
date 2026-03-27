from django.db import models
from meals.models import DietPlan


class MealForecast(models.Model):
    # 기존 구조 유지
    diet_plan = models.OneToOneField(
        DietPlan,
        on_delete=models.CASCADE,
        related_name="forecast"
    )
    predicted_count = models.IntegerField()
    reference_data = models.JSONField(null=True, blank=True)
    actual_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.diet_plan} 예측: {self.predicted_count}명"


class AttendancePrediction(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "조식"
        LUNCH = "lunch", "중식"
        DINNER = "dinner", "석식"

    prediction_date = models.DateField(verbose_name="예측 날짜")
    meal_type = models.CharField(
        max_length=20,
        choices=MealType.choices,
        verbose_name="끼니"
    )
    predicted_count = models.IntegerField(verbose_name="예측 인원")
    model_name = models.CharField(max_length=100, verbose_name="모델명")
    input_features = models.JSONField(default=dict, blank=True, verbose_name="입력 feature")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-prediction_date", "-created_at"]

    def __str__(self):
        return f"{self.prediction_date} {self.get_meal_type_display()} - {self.predicted_count}명"