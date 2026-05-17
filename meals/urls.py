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
    deduct_inventory_view,
    weekly_mealplan_create,
    search_menus_api,
    add_diet_menu_api,
    remove_diet_menu_api,
)

app_name = "meals"

urlpatterns = [
    path("", meal_home, name="meal_home"),
    path("menu_create/", menu_create, name="menu_create"),
    path("menu_list/", menu_list, name="menu_list"),
    path("recipe_create/", recipe_create, name="recipe_create"),
    path("mealplan_create/", mealplan_create, name="mealplan_create"),
    path("mealplan/weekly/", weekly_mealplan_create, name="weekly_mealplan_create"),
    path("api/menus/search/", search_menus_api, name="search_menus_api"),
    path("api/menus/add/", add_diet_menu_api, name="add_diet_menu_api"),
    path("api/menus/remove/", remove_diet_menu_api, name="remove_diet_menu_api"),
    path("mealplan_list/", mealplan_list, name="mealplan_list"),
    path("menus/<int:menu_id>/edit/", menu_update, name="menu_update"),
    path("menus/<int:menu_id>/delete/", menu_delete, name="menu_delete"),
    path("deduct_inventory/", deduct_inventory_view, name="deduct_inventory"),
]