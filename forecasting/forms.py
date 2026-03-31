from datetime import timedelta

from django import forms
from django.utils import timezone


class AttendancePredictionForm(forms.Form):
    prediction_date = forms.DateField(
        label="예측 날짜",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.fields["prediction_date"].initial = tomorrow


class PredictionFilterForm(forms.Form):
    target_date = forms.DateField(
        label="단일 날짜",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    start_date = forms.DateField(
        label="시작일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    end_date = forms.DateField(
        label="종료일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    order = forms.ChoiceField(
        label="정렬",
        required=False,
        choices=[
            ("latest", "최신순"),
            ("oldest", "오래된순"),
        ],
        initial="latest",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def clean(self):
        cleaned_data = super().clean()
        target_date = cleaned_data.get("target_date")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if target_date and (start_date or end_date):
            raise forms.ValidationError("단일 날짜 조회와 기간 조회는 동시에 사용할 수 없습니다.")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("시작일은 종료일보다 늦을 수 없습니다.")

        return cleaned_data