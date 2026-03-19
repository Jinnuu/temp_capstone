import os
import django
import pandas as pd

# 1. 장고 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import Ingredient
from accounts.models import User

def import_excel_data():
    supplier, _ = User.objects.get_or_create(
        username='samsung_welstory',
        defaults={'name': '삼성웰스토리', 'role': 'SUPPLIER'}
    )

    file_path = 'ingredients.xlsx'
    
    try:
        # 엑셀 파일 읽기 (5번째 줄이 헤더)
        df = pd.read_excel(file_path, header=4)
        
        # ✨ 핵심 마법: 엑셀 헤더의 모든 띄어쓰기와 양옆 공백을 싹 없애버립니다!
        # (예: '품 명' -> '품명', '규  격' -> '규격')
        df.columns = df.columns.str.replace(' ', '').str.strip()
        
        # 띄어쓰기를 없앤 이름('품명', '입찰단가')으로 빈칸 확인
        df = df.dropna(subset=['품명', '입찰단가'])
    except Exception as e:
        print(f"❌ 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        return

    success_count = 0
    print("📊 엑셀 데이터 분석 및 DB 저장 시작...")
    
    for index, row in df.iterrows():
        try:
            # 띄어쓰기가 제거된 컬럼명으로 데이터 가져오기
            raw_name = str(row['품명']).strip()
            spec = str(row['규격']).strip()
            unit = str(row['단위']).strip()
            
            if pd.isna(row['규격']) or spec == 'nan':
                full_name = raw_name
            else:
                full_name = f"{raw_name} ({spec})"
            
            # 가격 데이터 정제 (콤마 등 제거)
            raw_price = str(row['입찰단가']).replace(',', '').strip()
            price = int(float(raw_price))
            
            Ingredient.objects.update_or_create(
                name=full_name,
                defaults={
                    'unit': unit,
                    'unit_price': price,
                    'safe_stock_level': 10.0,
                    'supplier': supplier
                }
            )
            success_count += 1
            print(f"✔️ [저장 완료] {full_name} / {price}원")
            
        except Exception as e:
            # 에러가 나면 어떤 에러인지 정확히 출력
            print(f"⚠️ {index+6}번째 줄 건너뜀 (데이터 오류): {e}")

    print(f"\n✅ 대성공! 총 {success_count}개의 엑셀 식재료 데이터가 DB에 완벽하게 연동되었습니다!")

if __name__ == '__main__':
    import_excel_data()