from django.urls import path
from .views import procurement_home

urlpatterns = [
    path("", procurement_home, name="procurement_home"),
]