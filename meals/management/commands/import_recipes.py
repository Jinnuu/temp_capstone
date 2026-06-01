from pathlib import Path
from decimal import Decimal

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from inventory.models import Ingredient
from meals.models import Menu, Recipe


class Command(BaseCommand):
    help = "Import recipes from recipe Excel files without duplicates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help="Folder containing recipe Excel files. Default: BASE_DIR",
        )
        parser.add_argument(
            "--pattern",
            default="레시피*.xls*",
            help="Glob pattern for recipe files. Default: 레시피*.xls*",
        )

    def handle(self, *args, **options):
        base_dir = Path(options["path"] or settings.BASE_DIR)
        pattern = options["pattern"]
        files = sorted(base_dir.glob(pattern))

        if not files:
            self.stdout.write(
                self.style.WARNING(f"No recipe files found: {base_dir / pattern}")
            )
            return

        total_menus_created = 0
        total_recipes_created = 0
        total_files = 0

        existing_ingredients = list(Ingredient.objects.all())

        for file_path in files:
            total_files += 1
            self.stdout.write(f"Reading file: {file_path}")

            try:
                df = pd.read_excel(file_path, header=None)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to read {file_path}: {exc}"))
                continue

            for row_idx, row in df.iterrows():
                if row_idx == 0:
                    continue

                if len(row) <= 3:
                    continue

                menu_name = str(row[2]).strip() if pd.notna(row[2]) else ""
                ingredients_str = str(row[3]).strip() if pd.notna(row[3]) else ""

                if not menu_name or menu_name == "nan":
                    continue

                if menu_name in ["흑미밥하세요", "흑미밥", "백미밥"]:
                    continue

                if "하세요" in menu_name:
                    continue

                if "메" in menu_name and "뉴" in menu_name:
                    continue

                menu_obj, created = Menu.objects.get_or_create(name=menu_name)
                if created:
                    total_menus_created += 1

                if not ingredients_str or ingredients_str == "nan":
                    continue

                if menu_name == "야채달걀말이" and "고등어" in ingredients_str:
                    ingredients_str = "달걀, 당근, 양파, 대파, 소금"

                ingredient_names = [
                    item.strip()
                    for item in ingredients_str.split(",")
                    if item and item.strip()
                ]

                for ing_name in ingredient_names:
                    if not ing_name:
                        continue

                    if "재" in ing_name and "료" in ing_name:
                        continue

                    matched_ingredient = None

                    for ex_ing in existing_ingredients:
                        if ex_ing.name == ing_name:
                            matched_ingredient = ex_ing
                            break

                    if not matched_ingredient:
                        for ex_ing in existing_ingredients:
                            if ex_ing.name in ing_name or ing_name in ex_ing.name:
                                matched_ingredient = ex_ing
                                break

                    if matched_ingredient:
                        ingredient_obj = matched_ingredient
                    else:
                        ingredient_obj, _ = Ingredient.objects.get_or_create(
                            name=ing_name,
                            defaults={
                                "unit": "kg",
                                "spec": "기타",
                                "unit_price": 0,
                                "safe_stock_level": 0,
                            },
                        )
                        existing_ingredients.append(ingredient_obj)

                    _, recipe_created = Recipe.objects.get_or_create(
                        menu=menu_obj,
                        ingredient=ingredient_obj,
                        defaults={"required_amount": Decimal("0.10")},
                    )

                    if recipe_created:
                        total_recipes_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Files: {total_files}, created {total_menus_created} menus, "
                f"{total_recipes_created} recipe mappings."
            )
        )
