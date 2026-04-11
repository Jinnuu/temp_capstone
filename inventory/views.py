import openpyxl  
import re
from decimal import Decimal
from django.contrib import messages  
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField, Case, DecimalField, ExpressionWrapper, 
    F, Sum, Value, When, Q, IntegerField
)
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model 

from .forms import IngredientForm, InventoryLogForm
from .models import Ingredient, InventoryLog

User = get_user_model()
# 소수점 계산을 위한 기본값 설정
DECIMAL_ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))

def get_ingredient_stock_queryset():
    """
    재고 로그를 합산하여 실시간 현재고와 부족 상태를 계산하는 핵심 쿼리셋
    """
    return (
        Ingredient.objects.all()
        .annotate(
            # log_type이 '입고', '출고', '폐기'인 경우를 각각 합산
            in_qty=Coalesce(Sum(Case(When(inventorylog__log_type='입고', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
            out_qty=Coalesce(Sum(Case(When(inventorylog__log_type='출고', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
            waste_qty=Coalesce(Sum(Case(When(inventorylog__log_type='폐기', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        )
        .annotate(
            # 현재고 = 입고 - 출고 - 폐기
            current_stock=ExpressionWrapper(F("in_qty") - F("out_qty") - F("waste_qty"), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
        .annotate(
            # 안전재고보다 현재고가 작거나 같으면 부족(True)
            is_low_stock=Case(When(current_stock__lte=F("safe_stock_level"), then=Value(True)), default=Value(False), output_field=BooleanField())
        )
    )

def get_current_stock(ingredient_id):
    """특정 식재료의 현재고 숫자만 반환"""
    ingredient = get_ingredient_stock_queryset().get(pk=ingredient_id)
    return ingredient.current_stock

def ingredient_list(request):
    """식재료 목록 보기 (검색, 필터, 페이징, 전체 부족분 발주 기능 포함)"""
    selected_category = request.GET.get("category", "").strip()
    selected_supplier = request.GET.get("supplier", "").strip()
    search_query = request.GET.get("search", "").strip()
    sort_by = request.GET.get("sort", "status_priority") 

    # 1. 재고 계산이 포함된 기본 쿼리셋
    ingredients = get_ingredient_stock_queryset()

    # 2. 필터링
    if selected_category:
        ingredients = ingredients.filter(category=selected_category)
    if selected_supplier:
        ingredients = ingredients.filter(supplier__username=selected_supplier)
    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    # 3. [핵심] 전체 페이지 대상 부족분 ID 추출 (콤마로 연결)
    low_stock_ids = ingredients.filter(current_stock__lt=F('safe_stock_level')).values_list('id', flat=True)
    all_low_stock_ids = ",".join(map(str, low_stock_ids))

    # 4. 정렬 (부족 품목을 최상단으로)
    ingredients = ingredients.annotate(
        status_priority=Case(When(current_stock__lt=F('safe_stock_level'), then=Value(0)), default=Value(1), output_field=IntegerField())
    )

    if sort_by == "supplier":
        ingredients = ingredients.order_by("status_priority", "supplier__username", "id")
    elif sort_by == "name":
        ingredients = ingredients.order_by("status_priority", "name")
    else:
        ingredients = ingredients.order_by("status_priority", "-id")

    # 5. 필터용 데이터 (카테고리, 발주처)
    categories = Ingredient.objects.exclude(category__isnull=True).exclude(category__exact="").values_list("category", flat=True).distinct().order_by("category")
    suppliers = User.objects.filter(supplied_ingredients__isnull=False).distinct()

    # 6. 페이지네이션 (10개씩)
    paginator = Paginator(ingredients, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

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
    """신규 식재료 등록"""
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
    """엑셀 파일을 통한 식재료 일괄 등록/업데이트"""
    if request.method == "POST" and request.FILES.get("file"):
        excel_file = request.FILES["file"]
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            headers = [re.sub(r'\s*\(.*\)', '', str(cell.value)).strip() for cell in sheet[1]]
            
            col_map = {
                "식재료명": "name", "발주처": "supplier", "규격": "spec", "단위": "unit",
                "단가": "unit_price", "안전재고": "safe_stock_level", "대분류": "category",
                "연간예상소요량": "yearly_demand", "금액": "total_amount",
            }
            pos = {field: headers.index(name) if name in headers else None for name, field in col_map.items()}

            if pos["name"] is None:
                messages.error(request, "엑셀 파일에 '식재료명' 컬럼이 포함되어야 합니다.")
                return redirect("inventory:ingredient_create")

            success_count = 0
            for row in sheet.iter_rows(min_row=2, values_only=True):
                def get_val(field):
                    idx = pos.get(field)
                    return row[idx] if idx is not None else None

                name = get_val("name")
                if not name: continue
                
                supplier_val = get_val("supplier")
                supplier_obj = User.objects.filter(username=str(supplier_val).strip()).first() if supplier_val else None
                
                Ingredient.objects.update_or_create(
                    name=str(name).strip(),
                    defaults={
                        "supplier": supplier_obj, "spec": get_val("spec"), "unit": get_val("unit"),
                        "unit_price": Decimal(str(get_val("unit_price") or 0)),
                        "safe_stock_level": Decimal(str(get_val("safe_stock_level") or 0)),
                        "category": get_val("category"),
                        "yearly_demand": Decimal(str(get_val("yearly_demand") or 0)),
                        "total_amount": Decimal(str(get_val("total_amount") or 0)),
                    }
                )
                success_count += 1
            messages.success(request, f"{success_count}건의 데이터가 처리되었습니다.")
        except Exception as e:
            messages.error(request, f"오류 발생: {e}")
    return redirect("inventory:ingredient_list")

def inventory_log_create(request):
    """재고 출고 및 폐기 전용 등록 뷰 (검색창 및 최근 내역 포함)"""
    all_ingredients = get_ingredient_stock_queryset()
    recent_logs = InventoryLog.objects.filter(
        log_type__in=['출고', '폐기']
    ).select_related('ingredient').order_by('-transaction_date', '-id')[:15]

    if request.method == "POST":
        form = InventoryLogForm(request.POST)
        if form.is_valid():
            ingredient = form.cleaned_data["ingredient"]
            quantity = form.cleaned_data["quantity"]
            log_type = form.cleaned_data["log_type"]

            # 출고/폐기 시 재고 검증
            current_stock = get_current_stock(ingredient.id)
            if quantity > current_stock:
                form.add_error('quantity', f"현재고({current_stock})가 부족합니다.")
            else:
                form.save()
                messages.success(request, f"[{ingredient.name}] {log_type} 기록 완료.")
                return redirect("inventory:inventory_log_create")
    else:
        form = InventoryLogForm()

    return render(request, "inventory/inventory_log_form.html", {
        "form": form, "recent_logs": recent_logs, "ingredients": all_ingredients
    })