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
    path("", views.forecasting_home, name="home"),
    path("calendar/", views.prediction_calendar_view, name="prediction_calendar"),
    path("predict/", views.prediction_create_view, name="prediction_create"),
    path("results/", views.prediction_list_view, name="prediction_list"),
    path("results/<int:prediction_id>/", views.prediction_result_view, name="prediction_result"),
    path("ingredients/", views.ingredient_requirement_view, name="ingredient_requirement"),
]