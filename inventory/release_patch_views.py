from decimal import Decimal, InvalidOperation
import re

import pandas as pd
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import Ingredient


User = get_user_model()


def _norm(value):
    """엑셀 헤더/문자열 비교용 정규화."""
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    return text.lower()


def _to_decimal(value, default="0"):
    if value is None or value == "":
        return Decimal(default)

    try:
        text = str(value).replace(",", "").strip()
        if not text or text.lower() == "nan":
            return Decimal(default)
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _to_int(value, default=0):
    try:
        return int(_to_decimal(value, default=default))
    except Exception:
        return default


def _find_header_row(raw_df):
    """상단 제목행이 있어도 '식재료명'이 있는 행을 헤더로 인식."""
    for idx, row in raw_df.iterrows():
        normalized = [_norm(v) for v in row.tolist()]
        if "식재료명" in normalized or "재료명" in normalized or "품목명" in normalized:
            return idx
    return None


def _read_excel_with_flexible_header(upload_file):
    raw = pd.read_excel(upload_file, header=None, dtype=object)
    header_idx = _find_header_row(raw)

    if header_idx is None:
        raise ValueError("엑셀 파일에서 '식재료명' 또는 '품목명' 컬럼을 찾지 못했습니다.")

    headers = [str(v).strip() if v is not None and str(v) != "nan" else "" for v in raw.iloc[header_idx].tolist()]
    df = raw.iloc[header_idx + 1:].copy()
    df.columns = headers
    df = df.dropna(how="all")
    return df


def _get_existing_field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _find_supplier(value):
    if not value:
        return None

    value = str(value).strip()
    if not value or value.lower() == "nan":
        return None

    user_fields = _get_existing_field_names(User)
    query = Q(username=value)

    if "name" in user_fields:
        query |= Q(name=value)
    if "first_name" in user_fields:
        query |= Q(first_name=value)

    return User.objects.filter(query).first()


def ingredient_upload_flexible(request):
    """상단 제목행/공백/괄호가 있어도 식재료 엑셀을 읽는 업로드 view."""
    if request.method == "GET":
        return render(request, "inventory/ingredient_upload.html")

    excel_file = request.FILES.get("file")
    if not excel_file:
        messages.error(request, "업로드할 엑셀 파일을 선택해 주세요.")
        return redirect("inventory:ingredient_upload")

    if not excel_file.name.lower().endswith((".xlsx", ".xls")):
        messages.error(request, "엑셀 파일(.xlsx, .xls)만 업로드할 수 있습니다.")
        return redirect("inventory:ingredient_upload")

    alias = {
        "식재료명": "name",
        "재료명": "name",
        "품목명": "name",
        "대분류": "category",
        "분류": "category",
        "카테고리": "category",
        "발주처": "supplier",
        "공급업체": "supplier",
        "업체": "supplier",
        "규격": "spec",
        "단위": "unit",
        "단가": "unit_price",
        "안전재고": "safe_stock_level",
        "연간예상소요량": "yearly_demand",
        "연간예상사용량": "yearly_demand",
        "금액": "total_amount",
        "식품설명": "description",
        "식품 설명": "description",
        "설명": "description",
        "비고": "description",
    }

    try:
        df = _read_excel_with_flexible_header(excel_file)

        positions = {}
        for col in df.columns:
            key = _norm(col)
            for label, field in alias.items():
                if key == _norm(label) and field not in positions:
                    positions[field] = col

        if "name" not in positions:
            messages.error(
                request,
                "엑셀 파일에서 식재료명 컬럼을 찾지 못했습니다. 헤더명은 '식재료명', '재료명', '품목명' 중 하나로 작성해 주세요.",
            )
            return redirect("inventory:ingredient_upload")

        success_count = 0
        skipped_count = 0
        error_rows = []

        for row_no, (_, row) in enumerate(df.iterrows(), start=1):
            def get_value(field_name):
                col = positions.get(field_name)
                if col is None:
                    return None
                value = row.get(col)
                if pd.isna(value):
                    return None
                return value

            name = get_value("name")
            if not name or str(name).strip().lower() == "nan":
                skipped_count += 1
                continue

            try:
                supplier_obj = _find_supplier(get_value("supplier"))

                defaults = {
                    "supplier": supplier_obj,
                    "spec": str(get_value("spec") or "").strip(),
                    "unit": str(get_value("unit") or "EA").strip(),
                    "unit_price": _to_int(get_value("unit_price"), default=0),
                    "safe_stock_level": _to_decimal(get_value("safe_stock_level"), default="0"),
                    "category": str(get_value("category") or "").strip(),
                    "yearly_demand": _to_int(get_value("yearly_demand"), default=0),
                    "total_amount": _to_int(get_value("total_amount"), default=0),
                }

                description = get_value("description")
                if description is not None:
                    defaults["description"] = str(description).strip()

                Ingredient.objects.update_or_create(
                    name=str(name).strip(),
                    defaults=defaults,
                )
                success_count += 1

            except Exception as row_exc:
                skipped_count += 1
                error_rows.append(f"{row_no}행 {name}: {row_exc}")

        if success_count:
            messages.success(
                request,
                f"식자재 엑셀 업로드 완료: {success_count}건 처리, {skipped_count}건 건너뜀.",
            )
        else:
            messages.warning(request, "저장된 식자재가 없습니다. 엑셀 컬럼과 데이터를 확인해 주세요.")

        if error_rows:
            messages.warning(request, "일부 행은 제외되었습니다: " + " / ".join(error_rows[:5]))

    except Exception as exc:
        messages.error(request, f"엑셀 업로드 중 오류가 발생했습니다: {exc}")
        return redirect("inventory:ingredient_upload")

    return redirect("inventory:ingredient_list")
