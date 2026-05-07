import os
import pandas as pd
from django.core.management.base import BaseCommand
from inventory.models import Ingredient
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Import ingredients from 2019 price comparison Excel file'

    def handle(self, *args, **options):
        file_path = '2019학년도 1학기  단가비교(최종)8(박영숙-2).xls'
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Create or Get Supplier User
        supplier, _ = User.objects.get_or_create(
            username='kangwon',
            defaults={'first_name': '강원대학교', 'is_staff': False}
        )
        self.stdout.write(f"Supplier: {supplier.first_name} ({supplier.username})")

        xl = pd.ExcelFile(file_path)
        sheets = ['농산물', '공산품', '육류', '계육및 계란', '수산물', '곡류', '김치', '유제품']
        
        total_created = 0
        total_skipped = 0

        for sheet in sheets:
            if sheet not in xl.sheet_names:
                self.stdout.write(self.style.WARNING(f"Sheet {sheet} not found, skipping."))
                continue

            self.stdout.write(f"Processing sheet: {sheet}...")
            df = pd.read_excel(xl, sheet_name=sheet, header=None)
            
            # Find header to determine starting row
            header_idx = -1
            for i, row in df.iterrows():
                row_vals = [str(v) for v in row.values]
                if any("품명" in v or "규격" in v or "단위" in v for v in row_vals):
                    header_idx = i
                    break
            
            if header_idx == -1:
                self.stdout.write(self.style.WARNING(f"Could not find header in {sheet}, skipping."))
                continue

            # Process data rows after header
            # Col 1: Name, Col 2: Spec, Col 5: Unit, Col 8: Price
            data_rows = df.iloc[header_idx + 1:]
            
            with transaction.atomic():
                for _, row in data_rows.iterrows():
                    try:
                        name = str(row[1]).strip()
                        spec = str(row[2]).strip() if pd.notna(row[2]) else ""
                        unit = str(row[5]).strip() if pd.notna(row[5]) else ""
                        price_val = row[8]
                        
                        # Data Validation
                        if not name or name == 'nan' or name == '합계' or '인상율' in name:
                            continue
                        
                        # Skip if already exists
                        if Ingredient.objects.filter(name=name).exists():
                            total_skipped += 1
                            continue
                        
                        # Price conversion
                        try:
                            price = int(float(price_val)) if pd.notna(price_val) else 0
                        except:
                            price = 0
                            
                        # Create Ingredient
                        # unit is required in model
                        if not unit or unit == 'nan':
                            unit = "g" # fallback
                            
                        Ingredient.objects.create(
                            name=name,
                            spec=spec,
                            unit=unit,
                            unit_price=price,
                            safe_stock_level=0,
                            supplier=supplier,
                            category=sheet
                        )
                        total_created += 1
                    except Exception as e:
                        # self.stdout.write(f"Error in row: {e}")
                        pass

        self.stdout.write(self.style.SUCCESS(f"Import complete! Created {total_created} ingredients, skipped {total_skipped} duplicates."))
