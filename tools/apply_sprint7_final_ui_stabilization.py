from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_final_ui_stabilization")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"backup: {bak}")


def main():
    targets = [
        "meals/urls.py",
        "inventory/urls.py",
        "procurement/urls.py",
        "templates/partials/top_nav.html",
        "templates/meals/mealplan_create.html",
        "templates/meals/weekly_mealplan_create.html",
        "templates/meals/monthly_mealplan_create.html",
        "static/css/sprint7_meal_search.css",
    ]

    for rel in targets:
        backup(ROOT / rel)

    print("Backups created. Files from the zip should overwrite the project files.")
    print("\nRun:")
    print("  python manage.py check")
    print("  python manage.py runserver")
    print("\nCheck:")
    print("  /meals/mealplan_create/")
    print("  /meals/mealplan/weekly/")
    print("  /meals/mealplan/monthly/")
    print("  /meals/menu_list/")
    print("  /inventory/ingredients/")
    print("  /procurement/orders/")


if __name__ == "__main__":
    main()
