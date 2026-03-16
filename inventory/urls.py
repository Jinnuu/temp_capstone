from django.urls import path
from .views import ingredient_list

urlpatterns = [
    path("ingredients/", ingredient_list, name="ingredient_list"),
]