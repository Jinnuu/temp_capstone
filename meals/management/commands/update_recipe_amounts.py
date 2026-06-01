from pathlib import Path
from decimal import Decimal

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from meals.models import Recipe


class Command(BaseCommand):
    help = "Update Recipe.required_amount from Purchase Order Excel files and apply fallbacks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help='Folder containing Purchase Order files. Default: BASE_DIR / "Purchase Order"',
        )
        parser.add_argument(
            "--pattern",
            default="*.xls*",
            help="Glob pattern for Purchase Order files. Default: *.xls*",
        )

    def get_fallback_amount(self, ingredient_name):
        if not ingredient_name:
            return Decimal("0.05")

        ing = ingredient_name.replace(" ", "")

        meat_fish_keywords = [
            "돼지", "소", "닭", "고등어", "오징어", "갈치",
            "새우", "생선", "육", "고기",
        ]
        rice_grains_keywords = ["쌀", "밥", "콩", "보리", "밀가루", "수제비"]
        veg_keywords = [
            "배추", "무", "파", "양파", "두부", "호박",
            "당근", "버섯", "상추", "시금치", "오이", "감자", "고추",
        ]
        seasoning_keywords = [
            "소금", "설탕", "간장", "고추장", "가루", "소스",
            "기름", "식초", "마늘", "생강", "된장", "참기름",
            "통깨", "케찹", "마요네즈",
        ]

        if any(kw in ing for kw in seasoning_keywords):
            return Decimal("0.01")
        if any(kw in ing for kw in meat_fish_keywords):
            return Decimal("0.15")
        if any(kw in ing for kw in rice_grains_keywords):
            return Decimal("0.12")
        if any(kw in ing for kw in veg_keywords):
            return Decimal("0.04")

        return Decimal("0.05")

    def handle(self, *args, **options):
        base_dir = Path(options["path"] or (Path(settings.BASE_DIR) / "Purchase Order"))
        pattern = options["pattern"]
        files = sorted(base_dir.glob(pattern))

        if not files:
            self.stdout.write(self.style.WARNING(f"No Purchase Order files found: {base_dir / pattern}"))
            self.apply_fallback_only()
            return

        po_amounts = {}

        for file_path in files:
            self.stdout.write(f"Reading Purchase Order file: {file_path}")

            try:
                df = pd.read_excel(file_path, header=None)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Skip {file_path}: {exc}"))
                continue

            for _, row in df.iterrows():
                if len(row) < 5:
                    continue

                menu_name = str(row[2]).strip() if pd.notna(row[2]) else ""
                ing_name = str(row[3]).strip() if pd.notna(row[3]) else ""
                amount_val = str(row[4]).strip() if pd.notna(row[4]) else ""

                if "메" in menu_name and "뉴" in menu_name:
                    continue
                if "재" in ing_name and "료" in ing_name:
                    continue
                if not menu_name or not ing_name or not amount_val:
                    continue

                try:
                    amount_number = float(amount_val)
                    amount_kg = amount_number / 1000.0
                    if amount_kg <= 0:
                        continue
                    po_amounts[(menu_name, ing_name)] = Decimal(str(round(amount_kg, 3)))
                except ValueError:
                    continue

        updated_from_file = 0
        updated_from_fallback = 0

        all_recipes = Recipe.objects.select_related("menu", "ingredient").all()

        for recipe in all_recipes:
            menu_name = recipe.menu.name
            ing_name = recipe.ingredient.name

            found_amount = po_amounts.get((menu_name, ing_name))

            if not found_amount:
                for (po_menu, po_ing), amount in po_amounts.items():
                    if po_menu == menu_name and (po_ing in ing_name or ing_name in po_ing):
                        found_amount = amount
                        break

            if found_amount:
                if recipe.required_amount != found_amount:
                    recipe.required_amount = found_amount
                    recipe.save(update_fields=["required_amount"])
                    updated_from_file += 1
            else:
                if recipe.required_amount == Decimal("0.10"):
                    recipe.required_amount = self.get_fallback_amount(ing_name)
                    recipe.save(update_fields=["required_amount"])
                    updated_from_fallback += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated recipes: {updated_from_file} from files, "
                f"{updated_from_fallback} from smart fallbacks."
            )
        )

    def apply_fallback_only(self):
        updated = 0
        for recipe in Recipe.objects.select_related("ingredient").all():
            if recipe.required_amount == Decimal("0.10"):
                recipe.required_amount = self.get_fallback_amount(recipe.ingredient.name)
                recipe.save(update_fields=["required_amount"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Applied smart fallback amounts to {updated} recipes.")
        )
