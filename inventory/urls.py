from django.urls import path

from . import views
from .release_patch_views import ingredient_upload_flexible

app_name = "inventory"

urlpatterns = [
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path("ingredients/upload/", ingredient_upload_flexible, name="ingredient_upload"),
    path("upload/", ingredient_upload_flexible, name="ingredient_upload_legacy"),
    path("log/create/", views.inventory_log_create, name="inventory_log_create"),
    path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),
    path("reports/weekly/", views.weekly_inventory_report, name="weekly_inventory_report"),
    path("reports/monthly/", views.monthly_inventory_report, name="monthly_inventory_report"),
    path("reports/export/excel/", views.export_inventory_excel, name="export_inventory_excel"),
]
