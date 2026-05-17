import os
import pandas as pd
from django.core.management.base import BaseCommand
from meals.models import Menu, Recipe
from inventory.models import Ingredient
from django.db import transaction

class Command(BaseCommand):
    help = 'Import recipes from legacy Purchase Order Excel files'

    def handle(self, *args, **options):
        folder_path = 'Purchase Order'
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f"Folder not found: {folder_path}"))
            return

        files = [f for f in os.listdir(folder_path) if f.endswith(('.xlsx', '.xls'))]
        self.stdout.write(self.style.SUCCESS(f"Found {len(files)} files to process."))

        total_menus = 0
        total_recipes = 0

        for file_name in files:
            path = os.path.join(folder_path, file_name)
            self.stdout.write(f"Processing {file_name}...")
            
            try:
                # Load Excel file to get all sheet names
                xl = pd.ExcelFile(path)
                
                for sheet_name in xl.sheet_names:
                    # Skip clearly irrelevant sheets
                    if 'Sheet' in sheet_name and sheet_name != 'Sheet1':
                        continue
                        
                    df = xl.parse(sheet_name, header=None)
                    
                    # Forward fill Menu Name column (Col 2)
                    if 2 not in df.columns: continue
                    df[2] = df[2].ffill()
                    
                    # Filter for rows where Ingredient (Col 3) is present
                    if 3 not in df.columns: continue
                    df_clean = df[df[3].notna()]
                    
                    with transaction.atomic():
                        for _, row in df_clean.iterrows():
                            # Basic validation for column indices
                            if len(row) < 5: continue
                            
                            menu_name = str(row[2]).strip()
                            ing_name = str(row[3]).strip()
                            amount_raw = row[4]
                            
                            # Skip if menu_name or ing_name looks like a header or is too short
                            if not menu_name or not ing_name or menu_name == 'nan' or ing_name == 'nan':
                                continue
                            if menu_name in ['메뉴', '메         뉴', '메  뉴'] or ing_name == '재료':
                                continue
                            
                            # Extract numeric amount
                            try:
                                if isinstance(amount_raw, str):
                                    # Try to extract number from "40 g"
                                    amount = float(''.join(filter(lambda x: x.isdigit() or x == '.', amount_raw)))
                                else:
                                    amount = float(amount_raw)
                            except:
                                amount = 0.0
    
                            if amount <= 0:
                                continue
    
                            # Get or Create Ingredient
                            ingredient, _ = Ingredient.objects.get_or_create(
                                name=ing_name,
                                defaults={'unit': 'g', 'safe_stock_level': 0}
                            )
    
                            # Get or Create Menu
                            menu, created = Menu.objects.get_or_create(name=menu_name)
                            if created:
                                total_menus += 1
    
                            # Update or Create Recipe
                            _, created = Recipe.objects.update_or_create(
                                menu=menu,
                                ingredient=ingredient,
                                defaults={'required_amount': amount}
                            )
                            if created:
                                total_recipes += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing {file_name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Finished! Created {total_menus} new menus and {total_recipes} recipe mappings."))
