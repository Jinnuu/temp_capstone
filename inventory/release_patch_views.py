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

    from accounts.supplier_identity import eligible_order_accounts
    return eligible_order_accounts(User.objects.filter(query)).first()


def ingredient_upload_flexible(request):
    """기존 URL을 유지하며 제목행·다중 시트·CSV/XLS/XLSX를 처리한다."""
    from .services import process_ingredient_file_upload

    if request.method == "GET":
        return render(request, "inventory/ingredient_upload.html")
    uploaded = request.FILES.get("file") or next(iter(request.FILES.values()), None)
    if not uploaded:
        messages.error(request, "업로드할 식재료 파일을 선택해 주세요.")
        return redirect("inventory:ingredient_upload")
    try:
        created, updated = process_ingredient_file_upload(uploaded)
        messages.success(request, f"식재료 업로드 완료: 신규 {created}건, 수정 {updated}건")
    except Exception as exc:
        messages.error(request, f"식재료 업로드 중 오류가 발생했습니다: {exc}")
        return redirect("inventory:ingredient_upload")
    return redirect("inventory:ingredient_list")
