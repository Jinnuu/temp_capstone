from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path("log/create/", views.inventory_log_create, name="inventory_log_create"),
    path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),
    path('upload/', views.ingredient_upload, name='ingredient_upload'),
]