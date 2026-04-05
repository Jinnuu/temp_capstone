from django.urls import path

from . import views
from .views import (
    forecasting_home,
    prediction_calendar_view,
    prediction_create_view,
    prediction_result_view,
    prediction_list_view,
)

app_name = "forecasting"

urlpatterns = [
    path("", forecasting_home, name="forecasting_home"),
    path("calendar/", prediction_calendar_view, name="prediction_calendar"),
    path("predict/", prediction_create_view, name="prediction_create"),
    path("results/", prediction_list_view, name="prediction_list"),
    path("results/<int:prediction_id>/", prediction_result_view, name="prediction_result"),
    path("requirement/", views.ingredient_requirement_view, name="ingredient_requirement"),
]