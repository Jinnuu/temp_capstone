import csv
import io
import re
from decimal import Decimal, InvalidOperation
import openpyxl
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Ingredient

User = get_user_model()

# 컬럼 유연 매핑 테이블
COLUMN_MAPPING = {
    "식재료명": "name", "name": "name", "품명": "name", "식자재명": "name", "재료명": "name",
    "대분류": "category", "category": "category", "분류": "category", 
    "카테고리": "category", "구분": "category", "품목분류": "category", 
    "대분류명": "category", "분류명": "category", "카테고리명": "category", "상세분류": "category",
    "규격": "spec", "spec": "spec", "규격사항": "spec", "사양": "spec",
    "단위": "unit", "unit": "unit",
    "단가": "unit_price", "unit_price": "unit_price", "식자재단가": "unit_price", "단가(원)": "unit_price",
    "안전재고": "safe_stock_level", "safe_stock_level": "safe_stock_level", "안전재고량": "safe_stock_level",
    "연간예상소요량": "yearly_demand", "yearly_demand": "yearly_demand", "소요량": "yearly_demand", "연간소요량": "yearly_demand",
    "금액": "total_amount", "total_amount": "total_amount", "총금액": "total_amount",
    "발주처": "supplier", "supplier": "supplier", "공급업체": "supplier", "거래처": "supplier",
    "비고": "description", "설명": "description", "description": "description", "적요": "description",
}

GENERIC_SHEET_NAMES = {'sheet', 'sheet1', 'sheet 1', '시트', '시트1', 'table1', 'data', '전체'}

def clean_header(header_name):
    """헤더 텍스트의 괄호 및 공백 정리 (예: '단가 (원)' -> '단가')"""
    if not header_name:
        return ""
    cleaned = re.sub(r'\s*\(.*\)', '', str(header_name)).strip()
    return cleaned

def parse_number_field(val, field_name, default=0, is_decimal=False):
    """숫자형 필드 안전 변환"""
    if val is None or str(val).strip() == "" or str(val).strip().lower() == "none":
        return Decimal(str(default)) if is_decimal else int(default)
    
    clean_str = str(val).replace(',', '').strip()
    try:
        if is_decimal:
            return Decimal(clean_str)
        else:
            return int(float(clean_str))
    except (ValueError, InvalidOperation):
        raise ValueError(f"'{field_name}' 필드의 값({val})이 유효한 숫자 형식이 아닙니다.")

@transaction.atomic
def process_ingredient_file_upload(file_input):
    """
    엑셀(.xlsx, .xls) 또는 CSV 파일 데이터를 읽어 Ingredient DB 모델에 일괄 등록(Upsert)합니다.
    - 다중 시트 파싱 지원: 워크북의 모든 시트를 순회합니다.
    - 시트명 기반 카테고리 자동 추론: 행 데이터에 category가 없으면 시트명(Sheet Title)을 category로 자동 부여합니다.
    - 트랜잭션 원자성(@transaction.atomic)을 보장하여 오류 발생 시 전체 롤백 처리됩니다.
    
    :param file_input: UploadedFile 객체 또는 파일 경로(str / Path)
    :return: (created_count, updated_count) 튜플
    """
    file_name = getattr(file_input, 'name', str(file_input))
    ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
    
    if ext not in ['xlsx', 'xls', 'csv']:
        raise ValueError("지원하지 않는 파일 형식입니다. (.xlsx, .csv 파일만 지원합니다)")

    rows_data = []

    # 엑셀 파싱 (다중 시트 지원 및 시트명 카테고리 활용)
    if ext in ['xlsx', 'xls']:
        parsed_successfully = False
        try:
            wb = openpyxl.load_workbook(file_input, data_only=True)
            for sheet in wb.worksheets:
                sheet_title = sheet.title.strip() if sheet.title else ""
                default_sheet_category = sheet_title if sheet_title.lower() not in GENERIC_SHEET_NAMES else None
                
                raw_rows = list(sheet.iter_rows(values_only=True))
                if not raw_rows or len(raw_rows) < 2:
                    continue
                
                headers = [clean_header(cell) for cell in raw_rows[0]]
                for row in raw_rows[1:]:
                    if any(cell is not None for cell in row):
                        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]}
                        row_dict['__sheet_category__'] = default_sheet_category
                        rows_data.append(row_dict)
            parsed_successfully = True
        except Exception as openpyxl_err:
            try:
                import pandas as pd
                if hasattr(file_input, 'seek'):
                    file_input.seek(0)
                excel_file = pd.ExcelFile(file_input)
                for sheet_name in excel_file.sheet_names:
                    sheet_title = sheet_name.strip()
                    default_sheet_category = sheet_title if sheet_title.lower() not in GENERIC_SHEET_NAMES else None
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    if df.empty:
                        continue
                    headers = [clean_header(col) for col in df.columns]
                    for _, row in df.iterrows():
                        if any(pd.notna(val) for val in row):
                            row_dict = {headers[i]: (None if pd.isna(row[i]) else row[i]) for i in range(min(len(headers), len(row))) if headers[i]}
                            row_dict['__sheet_category__'] = default_sheet_category
                            rows_data.append(row_dict)
                parsed_successfully = True
            except Exception as pd_err:
                raise ValueError(f"엑셀 파일 읽기 실패: {str(openpyxl_err)}")
            
    elif ext == 'csv':
        try:
            if hasattr(file_input, 'read'):
                content = file_input.read()
                if isinstance(content, bytes):
                    try:
                        decoded = content.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        decoded = content.decode('cp949')
                else:
                    decoded = content
                file_obj = io.StringIO(decoded)
            else:
                file_obj = open(file_input, mode='r', encoding='utf-8-sig')

            reader = csv.reader(file_obj)
            raw_rows = list(reader)
            if not raw_rows:
                raise ValueError("CSV 파일이 비어 있습니다.")

            headers = [clean_header(cell) for cell in raw_rows[0]]
            for row in raw_rows[1:]:
                if any(cell.strip() for cell in row if cell):
                    row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]}
                    row_dict['__sheet_category__'] = None
                    rows_data.append(row_dict)
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"CSV 파일 읽기 실패: {str(e)}")

    if not rows_data:
        raise ValueError("처리할 데이터 행이 존재하지 않습니다.")

    # 컬럼 매핑 확인 (수집된 전체 행 중 식재료명 컬럼 존재 여부 체크)
    has_name_column = False
    for row in rows_data:
        for header in row.keys():
            if COLUMN_MAPPING.get(header) == "name":
                has_name_column = True
                break
        if has_name_column:
            break

    if not has_name_column:
        raise ValueError("파일 헤더에 '식재료명' (또는 name/품명) 컬럼이 포함되어 있어야 합니다.")

    # 성능 최적화: 발주처(User) Pre-fetch 캐싱
    users = User.objects.all()
    user_cache = {}
    for u in users:
        user_cache[u.username.strip().lower()] = u
        if u.first_name:
            user_cache[u.first_name.strip().lower()] = u

    # DB 일괄 업서트 (update_or_create)
    created_count = 0
    updated_count = 0

    for idx, row in enumerate(rows_data, start=2):
        extracted = {}
        for header, val in row.items():
            field_name = COLUMN_MAPPING.get(header)
            if field_name:
                extracted[field_name] = val

        name_val = str(extracted.get('name') or '').strip()
        if not name_val:
            continue  # 식재료명이 비어있는 행은 스킵

        spec = str(extracted.get('spec') or '').strip() if extracted.get('spec') else None
        description = str(extracted.get('description') or '').strip() if extracted.get('description') else None
        unit = str(extracted.get('unit') or 'EA').strip()
        
        # 행의 category가 없으면 시트명(__sheet_category__) fallback 적용
        category = str(extracted.get('category') or '').strip() if extracted.get('category') else None
        if not category and row.get('__sheet_category__'):
            category = str(row.get('__sheet_category__')).strip()

        unit_price = parse_number_field(extracted.get('unit_price'), f"{idx}행 단가", default=0, is_decimal=False)
        safe_stock_level = parse_number_field(extracted.get('safe_stock_level'), f"{idx}행 안전재고", default=0, is_decimal=True)
        yearly_demand = parse_number_field(extracted.get('yearly_demand'), f"{idx}행 연간예상소요량", default=0, is_decimal=False) if extracted.get('yearly_demand') is not None else None
        total_amount = parse_number_field(extracted.get('total_amount'), f"{idx}행 금액", default=0, is_decimal=False) if extracted.get('total_amount') is not None else None

        supplier_name = str(extracted.get('supplier') or '').strip().lower()
        supplier_obj = user_cache.get(supplier_name) if supplier_name else None

        defaults = {
            'spec': spec,
            'description': description,
            'unit': unit,
            'unit_price': unit_price,
            'safe_stock_level': safe_stock_level,
            'category': category,
            'yearly_demand': yearly_demand,
            'total_amount': total_amount,
            'supplier': supplier_obj,
        }

        obj, created = Ingredient.objects.update_or_create(
            name=name_val,
            defaults=defaults
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    return created_count, updated_count
