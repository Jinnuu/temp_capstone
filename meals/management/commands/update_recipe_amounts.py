import os
import glob
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from meals.models import Menu, Recipe

class Command(BaseCommand):
    help = 'Update Recipe required_amount from Purchase Order files and apply fallbacks.'

    def get_fallback_amount(self, ingredient_name):
        """Returns arbitrary realistic amount in kg for 1 person based on category keywords."""
        if not ingredient_name:
            return Decimal('0.05')
            
        ing = ingredient_name.replace(' ', '')
        
        meat_fish_keywords = ['돼지', '소', '닭', '고등어', '오징어', '갈치', '새우', '생선', '육', '고기']
        rice_grains_keywords = ['쌀', '밥', '콩', '보리', '밀가루', '수제비']
        veg_keywords = ['배추', '무', '파', '양파', '두부', '호박', '당근', '버섯', '상추', '시금치', '오이', '감자', '고추']
        seasoning_keywords = ['소금', '설탕', '간장', '고추장', '가루', '소스', '기름', '식초', '마늘', '생강', '된장', '참기름', '통깨', '케찹', '마요네즈']

        if any(kw in ing for kw in seasoning_keywords):
            return Decimal('0.01')  # 10g
        if any(kw in ing for kw in meat_fish_keywords):
            return Decimal('0.15')  # 150g
        if any(kw in ing for kw in rice_grains_keywords):
            return Decimal('0.12')  # 120g
        if any(kw in ing for kw in veg_keywords):
            return Decimal('0.04')  # 40g
            
        # Default fallback
        return Decimal('0.05')  # 50g

    def handle(self, *args, **options):
        base_dir = r"c:\temp_capstone-sprint5\Purchase Order"
        search_pattern = os.path.join(base_dir, "*.xls*")
        files = glob.glob(search_pattern)

        if not files:
            self.stdout.write(self.style.WARNING("No Purchase Order files found."))
            return

        recipes_updated_from_file = 0
        recipes_updated_from_fallback = 0

        # Create a dict to hold found combinations from PO files
        # Key: (menu_name_stripped, ingredient_name_stripped) -> value: amount_in_kg
        po_amounts = {}

        for file_path in files:
            try:
                # Read without header
                df = pd.read_excel(file_path, header=None)
            except Exception as e:
                continue

            for row_idx, row in df.iterrows():
                # Expected format around PO files:
                # Typically, index 2 = menu, index 3 = ingredient, index 4 = amount per person
                # But it can vary slightly. We will attempt a loose capture if "1인량" pattern matches.
                # However, our pilot script showed that '메뉴', '재료', '1인량' align roughly at index 2, 3, 4.
                if len(row) < 5:
                    continue
                    
                menu_name = str(row[2]) if pd.notna(row[2]) else ''
                ing_name = str(row[3]) if pd.notna(row[3]) else ''
                amount_val = str(row[4]) if pd.notna(row[4]) else ''
                
                # if row is a header row, break or skip
                if "메" in menu_name and "뉴" in menu_name:
                    continue
                if "재" in ing_name and "료" in ing_name:
                    continue

                menu_name = menu_name.strip()
                ing_name = ing_name.strip()
                amount_val = amount_val.strip()

                if not menu_name or not ing_name or not amount_val or not amount_val.replace('.','',1).isdigit():
                    continue

                try:
                    # In PO files, 1인량 is typically in grams (e.g. 80, 10, 5)
                    # Convert to kg
                    amount_kg = float(amount_val) / 1000.0
                    if amount_kg <= 0:
                        continue
                        
                    po_amounts[(menu_name, ing_name)] = Decimal(str(round(amount_kg, 3)))
                except ValueError:
                    pass

        # Now traverse ALL existing recipes in DB
        all_recipes = Recipe.objects.select_related('menu', 'ingredient').all()
        for recipe in all_recipes:
            menu_name = recipe.menu.name
            ing_name = recipe.ingredient.name
            
            # 1. Try to find an exact match from parsed data
            found_amount = po_amounts.get((menu_name, ing_name))
            
            # 2. If not exact, allow partial match for the ingredient within the same menu
            if not found_amount:
                for (po_m, po_i), amt in po_amounts.items():
                    if po_m == menu_name and (po_i in ing_name or ing_name in po_i):
                        found_amount = amt
                        break
            
            if found_amount:
                # Update from file data
                if recipe.required_amount != found_amount:
                    recipe.required_amount = found_amount
                    recipe.save()
                    recipes_updated_from_file += 1
            else:
                # 3. Apply Fallback if it is still at the default 0.10
                if recipe.required_amount == Decimal('0.10'):
                    fallback = self.get_fallback_amount(ing_name)
                    recipe.required_amount = fallback
                    recipe.save()
                    recipes_updated_from_fallback += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully updated recipes: {recipes_updated_from_file} from files, {recipes_updated_from_fallback} from smart fallbacks."
        ))
