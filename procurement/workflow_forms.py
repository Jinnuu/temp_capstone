from decimal import Decimal
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Ingredient, IngredientCategory, SupplySpecification
from meals.models import DietPlan, Menu, Recipe
from .workflow import convert, quantity


class HeadcountForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=DietPlan.objects.all().order_by('target_date','meal_type'), label='날짜·식사')
    manual = forms.IntegerField(min_value=0,max_value=1000000,label='직접 예상 식수')
    final = forms.IntegerField(min_value=0,max_value=1000000,required=False,label='최종 예상 식수')
    confirm = forms.BooleanField(required=False,label='최종 식수 확정 / 재확정')

    def clean(self):
        data=super().clean()
        if data.get('confirm') and data.get('final') is None:
            self.add_error('final','0명을 포함해 최종 식수를 입력하세요.')
        return data


class PreviewForm(forms.Form):
    start_date=forms.DateField(label='발주 시작일',widget=forms.DateInput(attrs={'type':'date'}))
    end_date=forms.DateField(label='발주 종료일',widget=forms.DateInput(attrs={'type':'date'}))
    days=forms.MultipleChoiceField(choices=[(str(i),name) for i,name in enumerate(['월','화','수','목','금'])],initial=['0','1','2','3','4'],widget=forms.CheckboxSelectMultiple,label='발주 요일')
    request_key=forms.UUIDField(widget=forms.HiddenInput)


class SpecificationForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        from accounts.supplier_identity import eligible_order_accounts
        self.fields['supplier'].queryset=eligible_order_accounts(self.fields['supplier'].queryset)

    class Meta:
        model=SupplySpecification
        fields=['ingredient','supplier','label','base_quantity','base_unit','order_unit','order_increment','unit_price']
        labels={'ingredient':'식재료','supplier':'공급업체','label':'브랜드·규격 설명','base_quantity':'포장 1단위의 내용량','base_unit':'내용량 단위 (kg/g/EA 등)','order_increment':'발주 간격 (캔=1, kg=0.01 등)', 'order_unit':'발주 단위 (캔/봉/개/kg 등)','unit_price':'포장 1단위 가격 (원)'}

    def clean(self):
        data=super().clean()
        ing=data.get('ingredient')
        try:
            if ing and data.get('base_quantity') is not None and data.get('base_unit'):
                quantity(data['base_quantity'],positive=True)
                convert(data['base_quantity'],data['base_unit'],ing.unit)
            if data.get('order_increment') is not None:
                quantity(data['order_increment'],'발주 간격',positive=True)
            if data.get('unit_price') is not None:
                quantity(data['unit_price'],'포장 가격')
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return data


class SupplierForm(forms.Form):
    username=forms.CharField(max_length=150,label='업체 식별자')
    name=forms.CharField(max_length=50,label='업체명')
    phone_number=forms.CharField(max_length=20,required=False,label='연락처')


class CategoryForm(forms.Form):
    name=forms.CharField(max_length=50,label='카테고리명')
    rename_from=forms.CharField(max_length=50,required=False,label='변경할 기존 분류명 (선택)')
    ingredients=forms.ModelMultipleChoiceField(queryset=Ingredient.objects.all().order_by('name'),required=False,label='이 분류로 정정할 식재료')


class InspectionForm(forms.Form):
    delivered=forms.DecimalField(max_digits=18,decimal_places=6,min_value=0,label='실제 납품량 (재고 기준 단위)')
    accepted=forms.DecimalField(max_digits=18,decimal_places=6,min_value=0,label='검수 합격량 / 실제 입고량')
    condition=forms.ChoiceField(choices=[('정상','정상'),('이상','이상'),('반품','반품')],label='상태')
    specification=forms.CharField(max_length=200,label='확인한 납품규격')
    notes=forms.CharField(required=False,widget=forms.Textarea,label='수량 차이·규격·품질 이상 사유')
    expiration=forms.DateField(required=False,widget=forms.DateInput(attrs={'type':'date'}),label='유통기한')


class TransactionForm(forms.Form):
    ingredient=forms.ModelChoiceField(queryset=Ingredient.objects.all().order_by('name'),label='식재료')
    kind=forms.ChoiceField(choices=[('입고','선입고 / 입고'),('출고','사용 출고'),('폐기','폐기'),('조정','재고 증가 조정')],label='거래')
    amount=forms.DecimalField(max_digits=18,decimal_places=6,min_value=Decimal('.000001'),label='수량 (등록 재고 단위)')
    when=forms.DateTimeField(initial=timezone.now,label='거래 일시')
    expiration=forms.DateField(required=False,label='유통기한',widget=forms.DateInput(attrs={'type':'date'}))
    notes=forms.CharField(required=False,label='사유')
    request_key=forms.UUIDField(widget=forms.HiddenInput)


class RecipeDetailForm(forms.ModelForm):
    class Meta:
        model=Recipe
        fields=['menu','ingredient','required_amount','unit']
        labels={'menu':'메뉴','ingredient':'식재료','required_amount':'1인분 기준량','unit':'기준량 단위 (공란이면 재고 기준 단위)'}

    def clean(self):
        data=super().clean();ing=data.get('ingredient')
        if ing and data.get('required_amount') is not None:
            try:
                quantity(data['required_amount'],positive=True)
                convert(data['required_amount'],data.get('unit') or ing.unit,ing.unit)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return data
