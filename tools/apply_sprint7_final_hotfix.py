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
        bak = path.with_suffix(path.suffix + ".bak_sprint7_final")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup: {bak}")


def ensure_inventory_imports():
    path = ROOT / "inventory" / "views.py"
    if not path.exists():
        print("skip: inventory/views.py not found")
        return

    text = read(path)
    backup(path)

    if "IngredientForm" not in text or "InventoryLogForm" not in text:
        # This check can be unreliable because the names may appear in function bodies.
        pass

    if "from .forms import IngredientForm, InventoryLogForm" not in text:
        if "from .models import Ingredient, InventoryLog" in text:
            text = text.replace(
                "from .models import Ingredient, InventoryLog",
                "from .forms import IngredientForm, InventoryLogForm\nfrom .models import Ingredient, InventoryLog",
                1,
            )
        else:
            # Fallback: put it before first local model import or near top
            text = "from .forms import IngredientForm, InventoryLogForm\n" + text

    # export_inventory_excel uses these names in sprint7, but some merged files miss the import.
    style_import = "from openpyxl.styles import Font, Alignment, Border, Side, PatternFill"
    if style_import not in text:
        if "import openpyxl" in text:
            text = text.replace("import openpyxl", "import openpyxl\n" + style_import, 1)
        else:
            text = style_import + "\n" + text

    # Some versions use PatternFill through openpyxl.styles.PatternFill;
    # importing it is harmless, but we keep both usages compatible.
    write(path, text)
    print("fixed: inventory/views.py imports")


def ensure_inventory_urls():
    path = ROOT / "inventory" / "urls.py"
    if not path.exists():
        print("skip: inventory/urls.py not found")
        return

    text = read(path)
    backup(path)

    # Fix the broken pk route created by a merge conflict / malformed patch.
    text = text.replace('path("ingredients//adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),',
                        'path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust"),')
    text = text.replace("path('ingredients//adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),",
                        "path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust'),")
    text = text.replace('path("ingredients//adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust_legacy"),',
                        'path("ingredients/<int:pk>/adjust/", views.ingredient_stock_adjust, name="ingredient_stock_adjust_legacy"),')
    text = text.replace("path('ingredients//adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust_legacy'),",
                        "path('ingredients/<int:pk>/adjust/', views.ingredient_stock_adjust, name='ingredient_stock_adjust_legacy'),")

    write(path, text)
    print("fixed: inventory/urls.py adjust route")


def main():
    ensure_inventory_imports()
    ensure_inventory_urls()
    print("\nOK: Sprint7 final hotfix patch applied.")
    print("Next:")
    print("  python manage.py check")
    print("  python manage.py runserver")


if __name__ == "__main__":
    main()
