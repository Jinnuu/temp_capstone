"""Atomic ingredient imports shared by the original and new upload routes."""
import csv
import io
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Ingredient

COLUMN_MAPPING = {}
for field, aliases in {
    'name': ['식재료명', '품명', '품목명', '식자재명', '재료명'],
    'category': ['대분류', '분류', '카테고리', '구분', '품목분류', '대분류명', '분류명', '카테고리명', '상세분류'],
    'spec': ['규격', '규격사항', '사양'], 'unit': ['단위'],
    'unit_price': ['단가', '식자재단가'], 'safe_stock_level': ['안전재고', '안전재고량'],
    'yearly_demand': ['연간예상소요량', '연간예상사용량', '소요량', '연간소요량'],
    'total_amount': ['금액', '총금액'], 'supplier': ['발주처', '공급업체', '거래처', '업체'],
    'description': ['식품설명', '비고', '설명', '적요'],
}.items():
    for alias in [field, *aliases]:
        COLUMN_MAPPING[alias] = field

GENERIC_SHEET_NAMES = {'sheet', 'sheet1', 'sheet 1', '시트', '시트1', 'table1', 'data', '전체'}


def clean_header(value):
    return re.sub(r'\s+', '', re.sub(r'\(.*?\)', '', str(value or ''))).lower().lstrip('\ufeff')


def parse_number_field(value, field_name, default=0, is_decimal=False):
    if value is None or str(value).strip().lower() in ('', 'none', 'nan'):
        value = default
    try:
        number = Decimal(str(value).replace(',', '').strip())
        if not number.is_finite():
            raise ValueError('non-finite number')
        return number if is_decimal else int(number)
    except (ValueError, InvalidOperation, OverflowError):
        raise ValueError(f"'{field_name}' 값({value})이 유효한 숫자가 아닙니다.")


def _mapped_rows(rows, sheet_name=None):
    rows = list(rows)
    for index, row in enumerate(rows):
        headers = [COLUMN_MAPPING.get(clean_header(value)) for value in row]
        if 'name' in headers:
            break
    else:
        return []
    category = sheet_name if sheet_name and sheet_name.lower() not in GENERIC_SHEET_NAMES else None
    result = []
    for row in rows[index + 1:]:
        record = {field: row[i] for i, field in enumerate(headers) if field and i < len(row)}
        if not record.get('category') and category:
            record['category'] = category
        result.append(record)
    return result


@transaction.atomic
def process_ingredient_file_upload(file_input):
    filename = getattr(file_input, 'name', str(file_input))
    ext = Path(filename).suffix.lower()
    records = []
    if ext == '.csv':
        raw = file_input.read() if hasattr(file_input, 'read') else Path(file_input).read_bytes()
        if isinstance(raw, bytes):
            try:
                raw = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                raw = raw.decode('cp949')
        records = _mapped_rows(csv.reader(io.StringIO(raw)))
    elif ext == '.xlsx':
        workbook = openpyxl.load_workbook(file_input, data_only=True)
        try:
            for sheet in workbook.worksheets:
                records.extend(_mapped_rows(sheet.iter_rows(values_only=True), sheet.title))
        finally:
            workbook.close()
    elif ext == '.xls':
        import pandas as pd
        with pd.ExcelFile(file_input, engine='xlrd') as workbook:
            for name in workbook.sheet_names:
                frame = workbook.parse(name, header=None, dtype=object)
                rows = [[None if pd.isna(value) else value for value in row] for row in frame.itertuples(index=False, name=None)]
                records.extend(_mapped_rows(rows, name))
    else:
        raise ValueError('지원하지 않는 파일 형식입니다. (.xlsx, .xls, .csv)')
    if not records:
        raise ValueError("식재료명 헤더와 데이터 행이 필요합니다.")

    users = {}
    for user in get_user_model().objects.all().order_by('id'):
        for key in (user.username, user.name, user.first_name):
            if key:
                users.setdefault(key.strip().lower(), user)
    created_count = updated_count = 0
    for row in records:
        name = str(row.get('name') or '').strip()
        if not name:
            continue
        defaults = {}
        # Missing columns preserve existing master data; supplied blanks clear nullable fields.
        for field in ('category', 'spec', 'description', 'unit'):
            if field in row:
                defaults[field] = str(row[field] or '').strip() or ('EA' if field == 'unit' else None)
        for field in ('unit_price', 'safe_stock_level', 'yearly_demand', 'total_amount'):
            if field in row:
                defaults[field] = parse_number_field(row[field], field, is_decimal=field == 'safe_stock_level')
        if 'supplier' in row:
            supplier_name = str(row['supplier'] or '').strip().lower()
            if supplier_name and supplier_name not in users:
                raise ValueError(f"등록되지 않은 공급업체입니다: {row['supplier']}")
            defaults['supplier'] = users.get(supplier_name)
        existing = Ingredient.objects.filter(name=name).first()
        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            if defaults:
                existing.save(update_fields=list(defaults))
            updated_count += 1
        else:
            initial = {'unit': 'EA', 'unit_price': 0, 'safe_stock_level': 0}
            initial.update(defaults)
            Ingredient.objects.create(name=name, **initial)
            created_count += 1
    return created_count, updated_count
