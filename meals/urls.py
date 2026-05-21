from django.urls import path

from .views import (
    add_diet_menu_api,
    deduct_inventory_view,
    meal_home,
    mealplan_create,
    mealplan_list,
    menu_create,
    menu_delete,
    menu_list,
    menu_update,
    recipe_create,
    remove_diet_menu_api,
    search_menus_api,
    weekly_mealplan_create,
)
from .views_extra import mealplan_bulk_upload, monthly_mealplan_create

app_name = "meals"

urlpatterns = [
    path("", meal_home, name="meal_home"),
    path("menu_create/", menu_create, name="menu_create"),
    path("menu_list/", menu_list, name="menu_list"),
    path("recipe_create/", recipe_create, name="recipe_create"),
    path("mealplan_create/", mealplan_create, name="mealplan_create"),
    path("mealplan/monthly/", monthly_mealplan_create, name="monthly_mealplan_create"),
    path("mealplan/weekly/", weekly_mealplan_create, name="weekly_mealplan_create"),
    path("mealplan/upload/", mealplan_bulk_upload, name="mealplan_bulk_upload"),
    path("api/menus/search/", search_menus_api, name="search_menus_api"),
    path("api/menus/add/", add_diet_menu_api, name="add_diet_menu_api"),
    path("api/menus/remove/", remove_diet_menu_api, name="remove_diet_menu_api"),
    path("mealplan_list/", mealplan_list, name="mealplan_list"),
    path("menus/<int:menu_id>/edit/", menu_update, name="menu_update"),
    path("menus/<int:menu_id>/delete/", menu_delete, name="menu_delete"),
    path("deduct_inventory/", deduct_inventory_view, name="deduct_inventory"),
]
