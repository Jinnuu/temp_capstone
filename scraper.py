import os
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import Ingredient
from accounts.models import User

def import_excel_data():
    supplier, _ = User.objects.get_or_create(username='samsung_welstory', defaults={'name': '삼성웰스토리', 'role': 'SUPPLIER'})
    file_path = 'ingredients.xlsx'
    
    try:
        df = pd.read_excel(file_path, header=4)
        df.columns = df.columns.str.replace(' ', '').str.strip()
        df = df.dropna(subset=['품명', '입찰단가'])
    except Exception as e:
        print(f"❌ 오류: {e}")
        return

    # ✨ 핵심: 이름과 규격이 분리된 새 데이터를 넣기 위해, 예전 찌꺼기 데이터를 싹 지워줍니다!
    print("🧹 기존 식재료 데이터를 초기화합니다...")
    Ingredient.objects.all().delete()

    success_count = 0
    print("📊 엑셀 데이터(이름/규격 분리) DB 연동 시작...")
    
    for index, row in df.iterrows():
        try:
            raw_name = str(row['품명']).strip()
            
            # 규격 데이터를 따로 빼냅니다!
            spec_val = str(row['규격']).strip()
            if pd.isna(row['규격']) or spec_val == 'nan':
                spec_val = ''
                
            unit = str(row['단위']).strip()
            category = str(row['대분류']).strip()
            
            raw_demand = str(row['연간예상소요량']).replace(',', '').strip()
            demand = int(float(raw_demand)) if raw_demand and raw_demand != 'nan' else 0
            
            raw_amount = str(row['금액']).replace(',', '').strip()
            amount = int(float(raw_amount)) if raw_amount and raw_amount != 'nan' else 0

            price = int(float(str(row['입찰단가']).replace(',', '').strip()))
            
            # DB 저장 (이제 name과 spec을 분리해서 각각의 칸에 쏙 넣습니다!)
            Ingredient.objects.create(
                name=raw_name,    # 품목명 (예: 쌈무)
                spec=spec_val,    # 규격 (예: 3kg,와사비맛)
                category=category,
                unit=unit,
                unit_price=price,
                yearly_demand=demand,
                total_amount=amount,
                safe_stock_level=10.0,
                supplier=supplier
            )
            success_count += 1
            
        except Exception as e:
            pass

    print(f"✅ 대성공! 총 {success_count}개의 데이터가 이름/규격 분리되어 저장되었습니다!")

if __name__ == '__main__':
    import_excel_data()