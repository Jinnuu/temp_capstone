
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_release_hotfix")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup: {bak.relative_to(ROOT)}")


def patch_inventory_imports():
    path = ROOT / "inventory" / "views.py"
    if not path.exists():
        print("skip inventory/views.py")
        return
    text = read(path)
    backup(path)

    if "IngredientForm" in text and "from .forms import" not in text:
        text = "from .forms import IngredientForm, InventoryLogForm\n" + text
    elif "from .forms import" in text and "IngredientForm" not in text.split("\n", 20)[0:20].__str__():
        text = re.sub(r"from \.forms import ([^\n]+)", lambda m: "from .forms import " + ", ".join(sorted(set([x.strip() for x in m.group(1).split(',')] + ["IngredientForm", "InventoryLogForm"]))), text, count=1)

    style_import = "from openpyxl.styles import Font, Alignment, Border, Side, PatternFill"
    if "Font(" in text and "from openpyxl.styles import" not in text:
        text = style_import + "\n" + text

    write(path, text)
    print("fixed inventory/views.py imports")


def patch_inventory_urls():
    path = ROOT / "inventory" / "urls.py"
    if not path.exists():
        print("skip inventory/urls.py")
        return
    text = read(path)
    backup(path)
    text = text.replace('path("ingredients//adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),', 'path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),')
    text = text.replace("path('ingredients//adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),", "path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),")
    text = text.replace('path("ingredients//adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust_legacy"),', 'path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust_legacy"),')
    text = text.replace("path('ingredients//adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust_legacy'),", "path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust_legacy'),")
    write(path, text)
    print("fixed inventory/urls.py")


def patch_meals_urls():
    path = ROOT / "meals" / "urls.py"
    if not path.exists():
        print("skip meals/urls.py")
        return
    text = read(path)
    backup(path)
    text = text.replace('path("api/menu//recipes/", get_menu_recipes_api, name="get_menu_recipes_api"),', 'path("api/menu/<int:menu_id>/recipes/", get_menu_recipes_api, name="get_menu_recipes_api"),')
    text = text.replace("path('api/menu//recipes/', get_menu_recipes_api, name='get_menu_recipes_api'),", "path('api/menu/<int:menu_id>/recipes/', get_menu_recipes_api, name='get_menu_recipes_api'),")
    text = text.replace('path("menus//edit/", menu_update, name="menu_update"),', 'path("menus/<int:pk>/edit/", menu_update, name="menu_update"),')
    text = text.replace('path("menus//delete/", menu_delete, name="menu_delete"),', 'path("menus/<int:pk>/delete/", menu_delete, name="menu_delete"),')
    text = text.replace("path('menus//edit/', menu_update, name='menu_update'),", "path('menus/<int:pk>/edit/', menu_update, name='menu_update'),")
    text = text.replace("path('menus//delete/', menu_delete, name='menu_delete'),", "path('menus/<int:pk>/delete/', menu_delete, name='menu_delete'),")
    write(path, text)
    print("fixed meals/urls.py")


def patch_meals_views_for_deduct_preview():
    path = ROOT / "meals" / "views.py"
    if not path.exists():
        print("skip meals/views.py")
        return
    text = read(path)
    backup(path)

    if "from inventory.models import Ingredient, InventoryLog" not in text:
        text = text.replace("from inventory.models import Ingredient", "from inventory.models import Ingredient, InventoryLog")

    # Decimal may already exist; timezone may not.
    if "from django.utils import timezone" not in text:
        text = "from django.utils import timezone\n" + text

    new_func = r