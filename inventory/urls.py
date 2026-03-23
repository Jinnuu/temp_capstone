from django.urls import path
from . import views  # 💡 바로 이 줄이 파이썬에게 views를 알려주는 핵심입니다!

app_name = 'inventory'

urlpatterns = [
    # 식재료 목록 화면
    path('ingredients/', views.ingredient_list, name='ingredient_list'),
    
    # 재고 입출고 등록 화면
    path('log/create/', views.inventory_log_create, name='inventory_log_create'), 
]