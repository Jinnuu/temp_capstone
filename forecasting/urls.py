from django.urls import path
from .views import forecasting_home

urlpatterns = [
    path("", forecasting_home, name="forecasting_home"),
]