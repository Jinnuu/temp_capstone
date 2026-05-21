import re
from decimal import Decimal, InvalidOperation

import openpyxl
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import IngredientForm, InventoryLogForm
from .models import Ingredient, InventoryLog


User = get_user_model()

DECIMAL_ZERO = Value(
    Decimal("0.00"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _to_decimal(value, default="0"):
    if value is None or value == "":
        return Decimal(default)

    try:
        cleaned = str(value).replace(",", "").strip()
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _clean_header(value):
    if value is None:
        return ""

    return re.sub(r"\s*\(.*\)", "", str(value)).strip()


def get_ingredient_stock_queryset():
    """재고 로그를 합산하여 실시간 현재고와 부족 상태를 계산한다."""
    return (
        Ingredient.objects.all()
        .annotate(
            in_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type="입고", then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            out_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type="출고", then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            waste_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type="폐기", then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            adj_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type="조정", then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
        )
        .annotate(
            calc_stock=ExpressionWrapper(
                F("in_qty") - F("out_qty") - F("waste_qty") + F("adj_qty"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .annotate(
            is_low_stock=Case(
                When(calc_stock__lte=F("safe_stock_level"), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
    )


def get_current_stock(ingredient_id):
    ingredient = get_ingredient_stock_queryset().get(pk=ingredient_id)
    return ingredient.calc_stock


def ingredient_list(request):
    """식자재 목록 보기."""
    selected_category = request.GET.get("category", "").strip()
    selected_supplier = request.GET.get("supplier", "").strip()
    search_query = request.GET.get("search", "").strip()
    sort_by = request.GET.get("sort", "status_priority")

    ingredients = get_ingredient_stock_queryset()

    if selected_category:
        ingredients = ingredients.filter(category=selected_category)

    if selected_supplier:
        ingredients = ingredients.filter(supplier__username=selected_supplier)

    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    low_stock_ids = ingredients.filter(calc_stock__lt=F("safe_stock_level")).values_list(
        "id",
        flat=True,
    )
    all_low_stock_ids = ",".join(map(str, low_stock_ids))

    ingredients = ingredients.annotate(
        status_priority=Case(
            When(calc_stock__lt=F("safe_stock_level"), then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )

    if sort_by == "supplier":
        ingredients = ingredients.order_by("status_priority", "supplier__username", "id")
    elif sort_by == "name":
        ingredients = ingredients.order_by("status_priority", "name")
    else:
        ingredients = ingredients.order_by("status_priority", "-id")

    categories = (
        Ingredient.objects.exclude(category__isnull=True)
        .exclude(category__exact="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    suppliers = User.objects.filter(supplied_ingredients__isnull=False).distinct()

    paginator = Paginator(ingredients, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "suppliers": suppliers,
        "selected_category": selected_category,
        "selected_supplier": selected_supplier,
        "search_query": search_query,
        "sort_by": sort_by,
        "all_low_stock_ids": all_low_stock_ids,
    }

    return render(request, "inventory/ingredient_list.html", context)


def ingredient_create(request):
    if request.method == "POST":
        form = IngredientForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "식재료가 성공적으로 등록되었습니다.")
            return redirect("inventory:ingredient_list")
    else:
        form = IngredientForm()

    return render(request, "inventory/ingredient_form.html", {"form": form})


def ingredient_upload(request):
    """식자재 기준정보를 엑셀 파일로 일괄 등록/수정한다."""
    if request.method == "GET":
        return render(request, "inventory/ingredient_upload.html")

    excel_file = request.FILES.get("file")

    if not excel_file:
        messages.error(request, "업로드할 엑셀(.xlsx) 파일을 선택해 주세요.")
        return redirect("inventory:ingredient_upload")

    if not excel_file.name.lower().endswith(".xlsx"):
        messages.error(request, "현재는 .xlsx 파일만 지원합니다.")
        return redirect("inventory:ingredient_upload")

    try:
        workbook = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = workbook.active

        headers = [_clean_header(cell.value) for cell in sheet[1]]

        col_map = {
            "식재료명": "name",
            "발주처": "supplier",
            "규격": "spec",
            "단위": "unit",
            "단가": "unit_price",
            "안전재고": "safe_stock_level",
            "대분류": "category",
            "연간예상소요량": "yearly_demand",
            "금액": "total_amount",
            "식품 설명": "description",
            "설명": "description",
        }

        positions = {}
        for excel_name, field_name in col_map.items():
            if excel_name in headers and field_name not in positions:
                positions[field_name] = headers.index(excel_name)

        if "name" not in positions:
            messages.error(request, "엑셀 파일에 '식재료명' 컬럼이 포함되어야 합니다.")
            return redirect("inventory:ingredient_upload")

        success_count = 0
        skipped_count = 0

        for row in sheet.iter_rows(min_row=2, values_only=True):
            def get_value(field_name):
                index = positions.get(field_name)
                return row[index] if index is not None else None

            name = get_value("name")

            if not name:
                skipped_count += 1
                continue

            supplier_value = get_value("supplier")
            supplier_obj = None

            if supplier_value:
                supplier_obj = User.objects.filter(
                    Q(username=str(supplier_value).strip())
                    | Q(name=str(supplier_value).strip())
                ).first()

            defaults = {
                "supplier": supplier_obj,
                "spec": get_value("spec") or "",
                "unit": get_value("unit") or "EA",
                "unit_price": int(_to_decimal(get_value("unit_price"))),
                "safe_stock_level": _to_decimal(get_value("safe_stock_level")),
                "category": get_value("category") or "",
                "yearly_demand": int(_to_decimal(get_value("yearly_demand"))),
                "total_amount": int(_to_decimal(get_value("total_amount"))),
            }

            description = get_value("description")
            if description is not None:
                defaults["description"] = str(description)

            Ingredient.objects.update_or_create(
                name=str(name).strip(),
                defaults=defaults,
            )
            success_count += 1

        messages.success(
            request,
            f"식자재 엑셀 업로드 완료: {success_count}건 처리, {skipped_count}건 건너뜀.",
        )

    except Exception as exc:
        messages.error(request, f"엑셀 업로드 중 오류가 발생했습니다: {exc}")
        return redirect("inventory:ingredient_upload")

    return redirect("inventory:ingredient_list")


def inventory_log_create(request):
    all_ingredients = get_ingredient_stock_queryset()
    recent_logs = (
        InventoryLog.objects.filter(log_type__in=["출고", "폐기"])
        .select_related("ingredient")
        .order_by("-transaction_date", "-id")[:15]
    )

    if request.method == "POST":
        form = InventoryLogForm(request.POST)

        if form.is_valid():
            ingredient = form.cleaned_data["ingredient"]
            quantity = form.cleaned_data["quantity"]
            log_type = form.cleaned_data["log_type"]
            current_stock = get_current_stock(ingredient.id)

            if log_type in ["출고", "폐기"] and quantity > current_stock:
                form.add_error("quantity", f"현재고({current_stock})가 부족합니다.")
            else:
                form.save()
                messages.success(request, f"[{ingredient.name}] {log_type} 기록 완료.")
                return redirect("inventory:inventory_log_create")
    else:
        form = InventoryLogForm()

    return render(
        request,
        "inventory/inventory_log_form.html",
        {
            "form": form,
            "recent_logs": recent_logs,
            "ingredients": all_ingredients,
        },
    )


def ingredient_stock_adjust(request, pk=None):
    """수동 재고 보정."""
    if request.method != "POST":
        return redirect("inventory:ingredient_list")

    ingredient = get_object_or_404(Ingredient, pk=pk)

    try:
        new_stock = Decimal(request.POST.get("new_stock", 0))
        current_val = get_current_stock(ingredient.id)
        diff = new_stock - current_val

        if diff != 0:
            InventoryLog.objects.create(
                ingredient=ingredient,
                log_type="조정",
                quantity=diff,
                description="수동 보정",
            )

        messages.success(request, f"{ingredient.name} 재고가 {new_stock}으로 수동 보정되었습니다.")

    except Exception as exc:
        messages.error(request, f"오류가 발생했습니다: {exc}")

    return redirect("inventory:ingredient_list")
