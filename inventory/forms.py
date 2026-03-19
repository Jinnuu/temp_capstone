from django import forms
from .models import InventoryLog

class InventoryLogForm(forms.ModelForm):
    class Meta:
        model = InventoryLog
        # 화면에 입력받을 칸들만 지정합니다 (시간은 장고가 알아서 현재 시간으로 찍어줍니다!)
        fields = ['ingredient', 'log_type', 'quantity', 'expiration_date']
        
        # 부트스트랩 디자인(CSS)을 입히고, 날짜 달력이 뜨도록 설정합니다.
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-select'}),
            'log_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        
        # 화면에 보여질 깔끔한 한글 라벨
        labels = {
            'ingredient': '식재료 선택',
            'log_type': '구분 (입고/출고/폐기)',
            'quantity': '수량',
            'expiration_date': '유통기한 (입고 시에만 입력)',
        }