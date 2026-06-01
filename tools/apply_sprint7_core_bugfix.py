from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_sprint7_core_bugfix")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup: {bak}")


def patch_inventory_views():
    path = ROOT / "inventory" / "views.py"
    if not path.exists():
        print("skip: inventory/views.py not found")
        return

    text = path.read_text(encoding="utf-8")
    backup(path)

    changed = False

    # 1) IngredientForm / InventoryLogForm import
    if "from .forms import IngredientForm, InventoryLogForm" not in text:
        if "from .models import Ingredient, InventoryLog" in text:
            text = text.replace(
                "from .models import Ingredient, InventoryLog",
                "from .forms import IngredientForm, InventoryLogForm\nfrom .models import Ingredient, InventoryLog",
                1,
            )
        elif "from .models import Ingredient" in text:
            text = text.replace(
                "from .models import Ingredient",
                "from .forms import IngredientForm, InventoryLogForm\nfrom .models import Ingredient",
                1,
            )
        else:
            text = "from .forms import IngredientForm, InventoryLogForm\n" + text
        changed = True

    # 2) openpyxl style imports used by export_inventory_excel()
    style_import = "from openpyxl.styles import Font, Alignment, Border, Side, PatternFill"
    if "from openpyxl.styles import" not in text:
        if "import openpyxl" in text:
            text = text.replace("import openpyxl", "import openpyxl\n" + style_import, 1)
        else:
            text = style_import + "\n" + text
        changed = True

    # 3) If code uses openpyxl.styles.PatternFill, it still works.
    #    If code uses bare PatternFill, import above fixes it.

    path.write_text(text, encoding="utf-8")
    if changed:
        print("fixed: inventory/views.py imports")
    else:
        print("ok: inventory/views.py already has required imports")


def patch_inventory_urls():
    path = ROOT / "inventory" / "urls.py"
    if not path.exists():
        print("skip: inventory/urls.py not found")
        return

    text = path.read_text(encoding="utf-8")
    backup(path)

    before = text
    text = text.replace(
        'path("ingredients//adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),',
        'path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),',
    )
    text = text.replace(
        "path('ingredients//adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),",
        "path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),",
    )

    path.write_text(text, encoding="utf-8")
    if text != before:
        print("fixed: inventory/urls.py malformed adjust route")
    else:
        print("ok: inventory/urls.py")


def main():
    patch_inventory_views()
    patch_inventory_urls()
    print("\nNext:")
    print("  python manage.py check")
    print("  python manage.py import_recipes --path .")
    print("  python manage.py update_recipe_amounts --path \"Purchase Order\"")


if __name__ == "__main__":
    main()
