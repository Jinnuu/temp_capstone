from django.urls import path
from . import views
from .views import (
    forecasting_home,
    prediction_create_view,
    prediction_result_view,
    prediction_list_view,
)

app_name = "forecasting"

urlpatterns = [
    path("", forecasting_home, name="forecasting_home"),
    path("predict/", prediction_create_view, name="prediction_create"),
    path("results/", prediction_list_view, name="prediction_list"),
    path("results/<int:prediction_id>/", prediction_result_view, name="prediction_result"),
    path('requirement/', views.ingredient_requirement_view, name='ingredient_requirement'),
]