from django.urls import path

from . import views
from .views import ingredient_upload
from .views_new_docs import doc_inventory_status

app_name = "inventory"

urlpatterns = [
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path("log/create/", views.inventory_log_create, name="inventory_log_create"),
    path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),
    path('upload/', views.ingredient_upload, name='ingredient_upload'),
    path('ingredients/upload/', ingredient_upload, name='ingredient_upload'),

    # 보고서 및 엑셀 출력 (기존)
    path('reports/weekly/', views.weekly_inventory_report, name='weekly_inventory_report'),
    path('reports/monthly/', views.monthly_inventory_report, name='monthly_inventory_report'),
    path('reports/export/excel/', views.export_inventory_excel, name='export_inventory_excel'),

    # [신규] 실무 문서 양식
    path('docs/inventory-status/', doc_inventory_status, name='doc_inventory_status'),
]