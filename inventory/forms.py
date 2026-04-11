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

    # 모델 필드를 ChoiceField로 덮어씌워 드롭다운으로 표시
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
            "category",      # 순서를 대분류부터 나오게 조정하면 입력이 더 자연스럽습니다
            "name",
            "supplier",      # 발주처 필드 유지
            "spec",
            "unit",
            "unit_price",
            "safe_stock_level",
            "yearly_demand",
            "total_amount",
        ]
        labels = {
            "category": "대분류",
            "name": "식재료명",
            "supplier": "발주처 (공급업체)", # 🔥 라벨 명확화
            "spec": "규격",
            "unit": "단위",
            "unit_price": "단가(원)",
            "safe_stock_level": "안전재고",
            "yearly_demand": "연간예상소요량",
            "total_amount": "금액",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "예: 국내산 돈육"}),
            "supplier": forms.Select(attrs={"class": "form-select"}), # 외래키이므로 Select 유지
            "spec": forms.TextInput(attrs={"class": "form-control", "placeholder": "예: 10kg/박스"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "safe_stock_level": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "yearly_demand": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "total_amount": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

    # 유효성 검사 로직 통합 및 간소화
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("식재료명은 필수 입력 항목입니다.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        # 0 이상의 값을 가져야 하는 필드들 리스트
        numeric_fields = ["unit_price", "safe_stock_level", "yearly_demand", "total_amount"]
        
        for field in numeric_fields:
            value = cleaned_data.get(field)
            if value is not None and value < 0:
                self.add_error(field, "0 이상의 숫자를 입력해주세요.")
        
        return cleaned_data


class InventoryLogForm(forms.ModelForm):
    # 출고와 폐기만 선택 가능하도록 커스텀 선택지 정의
    OUT_LOG_CHOICES = [
        ('출고', '출고 (사용)'),
        ('폐기', '폐기 (손실)'),
    ]

    # log_type 필드를 재정의하여 입고(IN)를 제거합니다.
    log_type = forms.ChoiceField(
        choices=OUT_LOG_CHOICES,
        label="구분",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = InventoryLog
        fields = ["ingredient", "log_type", "quantity"] # 출고 전용이므로 유통기한(expiration_date) 제외 가능
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
        }
        labels = {
            "ingredient": "출고 식재료 선택",
            "quantity": "출고 수량",
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= Decimal("0"):
            raise forms.ValidationError("수량은 0보다 커야 합니다.")
        return quantity