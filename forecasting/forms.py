from datetime import timedelta
from django import forms
from django.utils import timezone

from .models import AttendancePrediction


class AttendancePredictionForm(forms.Form):
    prediction_date = forms.DateField(
        label="예측 날짜",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    meal_type = forms.ChoiceField(
        label="끼니",
        choices=AttendancePrediction.MealType.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tomorrow = timezone.localdate() + timedelta(days=1)
        self.fields["prediction_date"].initial = tomorrow
        self.fields["meal_type"].initial = AttendancePrediction.MealType.LUNCH