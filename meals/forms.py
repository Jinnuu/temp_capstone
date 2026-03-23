from django import forms
from .models import Menu

class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['name', 'category']
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '예: 제육볶음'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '예: 한식, 일식, 양식'}),
        }
        
        labels = {
            'name': '메뉴명',
            'category': '메뉴 분류',
        }