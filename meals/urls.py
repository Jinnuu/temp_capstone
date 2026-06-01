from django.urls import path

from .recipe_file_views import (
    get_menu_recipes_api,
    recipe_upload_api,
    search_ingredients_api,
)
from .release_patch_views import (
    deduct_inventory_view,
    recipe_upload_page,
)
from .views import (
    add_diet_menu_api,
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
    weekly_meal_plan_document,
    monthly_meal_plan_document,
    export_weekly_mealplan_excel,
)
from .views_extra import mealplan_bulk_upload, monthly_mealplan_create

app_name = "meals"

urlpatterns = [
    path("", meal_home, name="meal_home"),

    path("menu_create/", menu_create, name="menu_create"),
    path("menu_list/", menu_list, name="menu_list"),
    path("recipe_create/", recipe_create, name="recipe_create"),

    path("menu/upload-excel/", recipe_upload_page, name="recipe_upload_page"),
    path("api/recipe/upload-excel/", recipe_upload_api, name="recipe_upload_api"),

    path("mealplan_create/", mealplan_create, name="mealplan_create"),
    path("mealplan/monthly/", monthly_mealplan_create, name="monthly_mealplan_create"),
    path("mealplan/weekly/", weekly_mealplan_create, name="weekly_mealplan_create"),
    path("mealplan/upload/", mealplan_bulk_upload, name="mealplan_bulk_upload"),
    path("mealplan_list/", mealplan_list, name="mealplan_list"),

    path("document/weekly/", weekly_meal_plan_document, name="weekly_meal_plan_document"),
    path("document/monthly/", monthly_meal_plan_document, name="monthly_meal_plan_document"),
    path("document/weekly/export/", export_weekly_mealplan_excel, name="export_weekly_mealplan_excel"),

    path("api/ingredients/search/", search_ingredients_api, name="search_ingredients_api"),
    path("api/menu/<int:menu_id>/recipes/", get_menu_recipes_api, name="get_menu_recipes_api"),
    path("api/menus/search/", search_menus_api, name="search_menus_api"),
    path("api/menus/add/", add_diet_menu_api, name="add_diet_menu_api"),
    path("api/menus/remove/", remove_diet_menu_api, name="remove_diet_menu_api"),

    path("menus/<int:menu_id>/edit/", menu_update, name="menu_update"),
    path("menus/<int:menu_id>/delete/", menu_delete, name="menu_delete"),

    path("deduct_inventory/", deduct_inventory_view, name="deduct_inventory"),
]
