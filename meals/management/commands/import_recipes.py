import os
import glob
import math
import pandas as pd
from django.core.management.base import BaseCommand
from meals.models import Menu, Recipe
from inventory.models import Ingredient
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import recipes from .xls files in the base directory without duplicates.'

    def handle(self, *args, **options):
        # Base directory where .xls files are located
        base_dir = r"c:\temp_capstone-sprint5"
        search_pattern = os.path.join(base_dir, "레시피*.xls*")
        files = glob.glob(search_pattern)

        if not files:
            self.stdout.write(self.style.WARNING("No recipe files found matching 레시피*.xls*"))
            return

        total_menus_created = 0
        total_recipes_created = 0
        
        # Pre-load all existing ingredients for loose matching
        existing_ingredients = list(Ingredient.objects.all())

        for file_path in files:
            self.stdout.write(f"Reading file: {os.path.basename(file_path)}")
            try:
                # Read without header
                df = pd.read_excel(file_path, header=None)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to read {file_path}: {e}"))
                continue

            # We assume column 2 (index 2) is Menu, column 3 (index 3) is Ingredients.
            # Row 0 usually contains the header "메   뉴". We'll just skip row 0.
            for row_idx, row in df.iterrows():
                if row_idx == 0:
                    continue  # skip header row

                if len(row) <= 3:
                    continue

                menu_name = str(row[2]) if not pd.isna(row[2]) else ""
                ingredients_str = str(row[3]) if not pd.isna(row[3]) else ""

                if not menu_name or not menu_name.strip() or menu_name.strip() == 'nan':
                    continue

                menu_name = menu_name.strip()
                # Skip descriptive / non-menu strings
                if menu_name in ['흑미밥하세요', '흑미밥', '백미밥'] or "하세요" in menu_name or "메" in menu_name and "뉴" in menu_name:
                    continue

                # get_or_create to prevent duplication
                menu_obj, created = Menu.objects.get_or_create(name=menu_name)
                if created:
                    total_menus_created += 1

                if not ingredients_str or not ingredients_str.strip() or ingredients_str.strip() == 'nan':
                    continue

                # Hotfix for legacy excel data typo (야채달걀말이 mistakenly matched with 고등어무조림 ingredients)
                if menu_name == '야채달걀말이' and '고등어' in ingredients_str:
                    ingredients_str = "달걀, 당근, 양파, 대파, 소금"

                ingredient_names = [i.strip() for i in ingredients_str.split(',') if i.strip()]
                
                for ing_name in ingredient_names:
                    # Ignore empty strings
                    if not ing_name or "재" in ing_name and "료" in ing_name:
                        continue
                        
                    # -----------------------------------------------------
                    # 식재료 품목에 있는 것을 위주로 레시피를 저장
                    # -----------------------------------------------------
                    matched_ingredient = None
                    # 1. Exact match
                    for ex_ing in existing_ingredients:
                        if ex_ing.name == ing_name:
                            matched_ingredient = ex_ing
                            break
                    
                    # 2. Contains match (e.g., DB has '돼지고기', excel has '돼지고기전지')
                    if not matched_ingredient:
                        for ex_ing in existing_ingredients:
                            # DB 식재료명이 엑셀 식재료명에 포함되어 있거나, 그 반대인 경우 가장 긴 것을 채택
                            if ex_ing.name in ing_name or ing_name in ex_ing.name:
                                matched_ingredient = ex_ing
                                break
                    
                    if matched_ingredient:
                        ingredient_obj = matched_ingredient
                    else:
                        # get_or_create Ingredient
                        ingredient_obj, _ = Ingredient.objects.get_or_create(
                            name=ing_name,
                            defaults={
                                'unit': 'kg', 
                                'spec': '기타',
                                'unit_price': 0,
                                'safe_stock_level': 0
                            }
                        )
                        existing_ingredients.append(ingredient_obj)  # Add to cache
                    
                    # Create the recipe mapping
                    recipe, r_created = Recipe.objects.get_or_create(
                        menu=menu_obj,
                        ingredient=ingredient_obj,
                        defaults={'required_amount': Decimal('0.10')}
                    )
                    if r_created:
                        total_recipes_created += 1

        self.stdout.write(self.style.SUCCESS(f"Done! Created {total_menus_created} Menus, {total_recipes_created} Recipe mappings without duplicates."))
