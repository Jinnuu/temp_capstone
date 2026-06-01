from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


URLS_CONTENT = 'from django.urls import path\n\nfrom .recipe_file_views import (\n    get_menu_recipes_api,\n    recipe_upload_api,\n    search_ingredients_api,\n)\nfrom .release_patch_views import (\n    deduct_inventory_view,\n    recipe_upload_page,\n)\nfrom .views import (\n    add_diet_menu_api,\n    meal_home,\n    mealplan_create,\n    mealplan_list,\n    menu_create,\n    menu_delete,\n    menu_list,\n    menu_update,\n    recipe_create,\n    remove_diet_menu_api,\n    search_menus_api,\n    weekly_mealplan_create,\n    weekly_meal_plan_document,\n    monthly_meal_plan_document,\n    export_weekly_mealplan_excel,\n)\nfrom .views_extra import mealplan_bulk_upload, monthly_mealplan_create\n\napp_name = "meals"\n\nurlpatterns = [\n    path("", meal_home, name="meal_home"),\n\n    path("menu_create/", menu_create, name="menu_create"),\n    path("menu_list/", menu_list, name="menu_list"),\n    path("recipe_create/", recipe_create, name="recipe_create"),\n\n    # 레시피 엑셀 업로드: 사용자 화면 + 기존 API 보존\n    path("menu/upload-excel/", recipe_upload_page, name="recipe_upload_page"),\n    path("api/recipe/upload-excel/", recipe_upload_api, name="recipe_upload_api"),\n\n    path("mealplan_create/", mealplan_create, name="mealplan_create"),\n    path("mealplan/monthly/", monthly_mealplan_create, name="monthly_mealplan_create"),\n    path("mealplan/weekly/", weekly_mealplan_create, name="weekly_mealplan_create"),\n    path("mealplan/upload/", mealplan_bulk_upload, name="mealplan_bulk_upload"),\n    path("mealplan_list/", mealplan_list, name="mealplan_list"),\n\n    path("document/weekly/", weekly_meal_plan_document, name="weekly_meal_plan_document"),\n    path("document/monthly/", monthly_meal_plan_document, name="monthly_meal_plan_document"),\n    path("document/weekly/export/", export_weekly_mealplan_excel, name="export_weekly_mealplan_excel"),\n\n    path("api/ingredients/search/", search_ingredients_api, name="search_ingredients_api"),\n    path("api/menu/<int:menu_id>/recipes/", get_menu_recipes_api, name="get_menu_recipes_api"),\n    path("api/menus/search/", search_menus_api, name="search_menus_api"),\n    path("api/menus/add/", add_diet_menu_api, name="add_diet_menu_api"),\n    path("api/menus/remove/", remove_diet_menu_api, name="remove_diet_menu_api"),\n\n    path("menus/<int:menu_id>/edit/", menu_update, name="menu_update"),\n    path("menus/<int:menu_id>/delete/", menu_delete, name="menu_delete"),\n\n    # 식사 완료 후 재고 차감: preview-confirm 방식\n    path("deduct_inventory/", deduct_inventory_view, name="deduct_inventory"),\n]\n'


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_recipe_deduct_patch")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup: {bak}")


def main():
    urls = ROOT / "meals" / "urls.py"
    backup(urls)
    urls.write_text(URLS_CONTENT, encoding="utf-8")
    print("fixed: meals/urls.py")

    print("\nNext:")
    print("  python manage.py check")
    print("  python manage.py runserver")
    print("\nCheck:")
    print("  /meals/menu_list/")
    print("  /meals/menu/upload-excel/")
    print("  /meals/deduct_inventory/?date=2026-06-01&meal_type=중식")


if __name__ == "__main__":
    main()
