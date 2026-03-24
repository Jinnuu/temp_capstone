from django import forms
from .models import Menu, DietPlan


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ["name", "category"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control form-control-lg",
                "placeholder": "예: 제육볶음"
            }),
            "category": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "예: 한식, 일식, 양식"
            }),
        }
        labels = {
            "name": "메뉴명",
            "category": "메뉴 분류",
        }


class MealPlanForm(forms.Form):
    target_date = forms.DateField(
        label="식단 날짜",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control"
        })
    )
    meal_type = forms.ChoiceField(
        label="끼니",
        choices=DietPlan.MealType.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    menus = forms.ModelMultipleChoiceField(
        label="메뉴 선택",
        queryset=Menu.objects.all().order_by("name"),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )