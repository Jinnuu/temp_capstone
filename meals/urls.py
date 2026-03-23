from django.urls import path
from .views import (
    meal_home,
    menu_create,
    menu_list,
    recipe_create,
    mealplan_create,
    mealplan_list,
    menu_delete, 
    menu_update,
)

app_name = "meals"

urlpatterns = [
    path("", meal_home, name="meal_home"),
    path("menu_create/", menu_create, name="menu_create"),
    path("menu_list/", menu_list, name="menu_list"),
    path("recipe_create/", recipe_create, name="recipe_create"),
    path("mealplan_create/", mealplan_create, name="mealplan_create"),
    path("mealplan_list/", mealplan_list, name="mealplan_list"),
    path("meals/<int:menu_id>/edit/", menu_update, name="menu_update"),
    # 💡 views. 를 빼고 깔끔하게 menu_delete만 적어줍니다!
    path("menus/<int:menu_id>/delete/", menu_delete, name="menu_delete"),
]