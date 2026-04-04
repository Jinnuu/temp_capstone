from decimal import Decimal
from django import forms
from .models import Ingredient, InventoryLog

class IngredientForm(forms.ModelForm):
    UNIT_CHOICES = [
        ('', '--- 단위 선택 ---'),
        ('kg', 'kg'),
        ('g', 'g'),
        ('EA', 'EA'),
        ('병', '병'),
        ('통', '통'),
        ('팩', '팩'),
        ('box','box'),

    ]

    CATEGORY_CHOICES = [
        ('', '--- 대분류 선택 ---'),
        ('과일류', '과일류'),
        ('기타식품', '기타식품'),
        ('김치/절임류', '김치/절임류'),
        ('냉동식품/즉석식품', '냉동식품/즉석식품'),
        ('병/통조림류', '병/통조림류'),
        ('소모품', '소모품'),
        ('수산/수산가공품', '수산/수산가공품'),
        ('양곡/곡분가공품', '양곡/곡분가공품'),
        ('양념/조미료류', '양념/조미료류'),
        ('유가공/음료제품', '유가공/음료제품'),
        ('채소/농가공품', '채소/농가공품'),
        ('축산/축산가공품', '축산/축산가공품'),
    ]

    unit = forms.ChoiceField(
        choices=UNIT_CHOICES,
        label="단위",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        label="대분류",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "spec",
            "unit",
            "unit_price",
            "safe_stock_level",
            "category",
            "yearly_demand",
            "total_amount",
        ]
        labels = {
            "name": "식재료명",
            "spec": "규격",
            "unit": "단위",
            "unit_price": "단가(원)",
            "safe_stock_level": "안전재고",
            "category": "대분류",
            "yearly_demand": "연간예상소요량",
            "total_amount": "금액",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "spec": forms.TextInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "safe_stock_level": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "yearly_demand": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_amount": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("식재료명은 비워둘 수 없습니다.")
        return name

    def clean_unit_price(self):
        value = self.cleaned_data["unit_price"]
        if value < 0:
            raise forms.ValidationError("단가는 0 이상이어야 합니다.")
        return value

    def clean_safe_stock_level(self):
        value = self.cleaned_data["safe_stock_level"]
        if value < 0:
            raise forms.ValidationError("안전재고는 0 이상이어야 합니다.")
        return value

    def clean_yearly_demand(self):
        value = self.cleaned_data.get("yearly_demand")
        if value is not None and value < 0:
            raise forms.ValidationError("연간예상소요량은 0 이상이어야 합니다.")
        return value

    def clean_total_amount(self):
        value = self.cleaned_data.get("total_amount")
        if value is not None and value < 0:
            raise forms.ValidationError("금액은 0 이상이어야 합니다.")
        return value


class InventoryLogForm(forms.ModelForm):
    class Meta:
        model = InventoryLog
        fields = ["ingredient", "log_type", "quantity", "expiration_date"]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "log_type": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "expiration_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "ingredient": "식재료 선택",
            "log_type": "구분 (입고/출고/폐기)",
            "quantity": "수량",
            "expiration_date": "유통기한 (입고 시에만 입력)",
        }

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity <= Decimal("0"):
            raise forms.ValidationError("수량은 0보다 커야 합니다.")
        return quantity