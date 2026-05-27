import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font
from django.http import HttpResponse  
import re
from datetime import timedelta, datetime, date
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages  
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField, Case, DecimalField, ExpressionWrapper, 
    F, Sum, Value, When, Q, IntegerField
)
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import get_user_model 

from .forms import IngredientForm, InventoryLogForm
from .models import Ingredient, InventoryLog

User = get_user_model()
# 소수점 계산을 위한 기본값 설정
DECIMAL_ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))

def get_ingredient_stock_queryset():
    """
    재고 로그를 합산하여 실시간 현재고와 부족 상태를 계산하는 핵심 쿼리셋.
    'calc_stock'이라는 이름을 사용하여 모델의 기존 필드와 충돌을 방지합니다.
    """
    return (
        Ingredient.objects.all()
        .annotate(
            # 각 로그 타입별 합산
            in_qty=Coalesce(Sum(Case(When(inventorylog__log_type='입고', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
            out_qty=Coalesce(Sum(Case(When(inventorylog__log_type='출고', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
            waste_qty=Coalesce(Sum(Case(When(inventorylog__log_type='폐기', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
            adj_qty=Coalesce(Sum(Case(When(inventorylog__log_type='조정', then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        )
        .annotate(
            # 🔥 모델 필드 current_stock과 충돌을 피하기 위해 calc_stock 사용
            calc_stock=ExpressionWrapper(
                F("in_qty") - F("out_qty") - F("waste_qty") + F("adj_qty"), 
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
        .annotate(
            # 안전재고 부족 여부 판단 (calc_stock 기준)
            is_low_stock=Case(
                When(calc_stock__lte=F("safe_stock_level"), then=Value(True)), 
                default=Value(False), 
                output_field=BooleanField()
            )
        )
    )

def get_current_stock(ingredient_id):
    """특정 식재료의 실시간 계산된 재고 숫자만 반환"""
    ingredient = get_ingredient_stock_queryset().get(pk=ingredient_id)
    return ingredient.calc_stock # 🔥 current_stock에서 calc_stock으로 변경

def ingredient_list(request):
    """식재료 목록 보기 (검색, 필터, 페이징, 전체 부족분 발주 기능 포함)"""
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

    # [핵심] 전체 페이지 대상 부족분 ID 추출 (calc_stock 기준 필터링)
    low_stock_ids = ingredients.filter(calc_stock__lt=F('safe_stock_level')).values_list('id', flat=True)
    all_low_stock_ids = ",".join(map(str, low_stock_ids))

    # 정렬용 우선순위 설정 (calc_stock 기준)
    ingredients = ingredients.annotate(
        status_priority=Case(
            When(calc_stock__lt=F('safe_stock_level'), then=Value(0)), 
            default=Value(1), 
            output_field=IntegerField()
        )
    )

    if sort_by == "supplier":
        ingredients = ingredients.order_by("status_priority", "supplier__username", "id")
    elif sort_by == "name":
        ingredients = ingredients.order_by("status_priority", "name")
    else:
        ingredients = ingredients.order_by("status_priority", "-id")

    categories = Ingredient.objects.exclude(category__isnull=True).exclude(category__exact="").values_list("category", flat=True).distinct().order_by("category")
    suppliers = User.objects.filter(supplied_ingredients__isnull=False).distinct()

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

            current_stock = get_current_stock(ingredient.id)
            if log_type in ['출고', '폐기'] and quantity > current_stock:
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

def ingredient_stock_adjust(request, pk):
    """수동 재고 보정 (calc_stock 기준 차이 계산)"""
    if request.method == "POST":
        ingredient = get_object_or_404(Ingredient, pk=pk)
        try:
            new_stock = Decimal(request.POST.get("new_stock", 0))
            current_val = get_current_stock(ingredient.id)
            diff = new_stock - current_val
            
            if diff != 0:
                InventoryLog.objects.create(
                    ingredient=ingredient,
                    log_type='조정',
                    quantity=diff,
                    description="수동 보정"
                )
                messages.success(request, f"{ingredient.name} 재고가 {new_stock}으로 수동 보정되었습니다.")
        except Exception as e:
            messages.error(request, f"오류가 발생했습니다: {e}")
    return redirect("inventory:ingredient_list")

# --- 수불 현황 보고서 및 엑셀 출력 ---

def weekly_inventory_report(request):
    """주간수불명세서 조회 뷰 (월~일 집계)"""
    target_date_str = request.GET.get('date', timezone.now().date().isoformat())
    try:
        requested_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        requested_date = timezone.now().date()

    # 해당 주의 월요일 계산
    monday = requested_date - timedelta(days=requested_date.weekday())
    sunday = monday + timedelta(days=6)
    
    # 시간대 고려한 범위 설정 (월요일 00:00:00 ~ 일요일 23:59:59)
    start_dt = timezone.make_aware(datetime.combine(monday, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(sunday, datetime.max.time()))

    ingredients = Ingredient.objects.all().order_by('category', 'name')
    report_data = []

    for item in ingredients:
        # 기초 재고 (월요일 시작 전)
        prev_stock = InventoryLog.objects.filter(ingredient=item, transaction_date__lt=start_dt).aggregate(
            total=Sum(Case(
                When(log_type='입고', then=F('quantity')),
                When(log_type='출고', then=-F('quantity')),
                When(log_type='폐기', then=-F('quantity')),
                When(log_type='조정', then=F('quantity')),
                default=Value(0),
                output_field=DecimalField()
            ))
        )['total'] or Decimal('0.00')

        # 주간 수불 내역 (%)
        week_logs = InventoryLog.objects.filter(ingredient=item, transaction_date__range=(start_dt, end_dt))
        in_qty = week_logs.filter(log_type='입고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        out_qty = (week_logs.filter(log_type='출고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')) + \
                  (week_logs.filter(log_type='폐기').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00'))
        adj_qty = week_logs.filter(log_type='조정').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')

        curr_stock = prev_stock + in_qty - out_qty + adj_qty

        if prev_stock != 0 or in_qty != 0 or out_qty != 0 or adj_qty != 0:
            report_data.append({
                'ingredient': item,
                'prev_stock': prev_stock,
                'in_qty': in_qty,
                'out_qty': out_qty,
                'adj_qty': adj_qty,
                'curr_stock': curr_stock,
            })

    context = {
        'monday': monday,
        'sunday': sunday,
        'target_date': requested_date,
        'report_data': report_data,
        'prev_week_date': (monday - timedelta(days=7)).isoformat(),
        'next_week_date': (monday + timedelta(days=7)).isoformat(),
    }
    return render(request, 'docs/weekly_inventory_report.html', context)

def monthly_inventory_report(request):
    """월수불명세서 조회 뷰"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))

    ingredients = Ingredient.objects.all().order_by('category', 'name')
    report_data = []

    for item in ingredients:
        # 기초 재고 (월초 이전)
        prev_stock = InventoryLog.objects.filter(ingredient=item, transaction_date__lt=start_dt).aggregate(
            total=Sum(Case(
                When(log_type='입고', then=F('quantity')),
                When(log_type='출고', then=-F('quantity')),
                When(log_type='폐기', then=-F('quantity')),
                When(log_type='조정', then=F('quantity')),
                default=Value(0),
                output_field=DecimalField()
            ))
        )['total'] or Decimal('0.00')

        # 당월 수불 내역
        month_logs = InventoryLog.objects.filter(ingredient=item, transaction_date__range=(start_dt, end_dt))
        in_qty = month_logs.filter(log_type='입고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        out_qty = (month_logs.filter(log_type='출고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')) + \
                  (month_logs.filter(log_type='폐기').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00'))
        adj_qty = month_logs.filter(log_type='조정').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')

        curr_stock = prev_stock + in_qty - out_qty + adj_qty

        if prev_stock != 0 or in_qty != 0 or out_qty != 0 or adj_qty != 0:
            report_data.append({
                'ingredient': item,
                'prev_stock': prev_stock,
                'in_qty': in_qty,
                'out_qty': out_qty,
                'adj_qty': adj_qty,
                'curr_stock': curr_stock,
            })

    context = {
        'year': year,
        'month': month,
        'report_data': report_data,
    }
    return render(request, 'docs/monthly_inventory_report.html', context)

def export_inventory_excel(request):
    """수불 내역 엑셀 다운로드 (주간/월간 지원)"""
    report_type = request.GET.get('type', 'weekly')
    target_date_str = request.GET.get('date', timezone.now().date().isoformat())
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "수불명세서"

    # 헤더 스타일
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    headers = ["No", "분류", "식재료명", "규격", "단위", "기초재고", "입고합계", "출고합계", "보정액", "기말재고", "비고"]
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = alignment
        cell.border = thin_border

    # 범위 설정
    if report_type == 'monthly':
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        filename = f"Inventory_Report_Monthly_{year}_{month}.xlsx"
    else: # weekly
        requested_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        monday = requested_date - timedelta(days=requested_date.weekday())
        sunday = monday + timedelta(days=6)
        start_date = monday
        end_date = sunday + timedelta(days=1)
        filename = f"Inventory_Report_Weekly_{monday.isoformat()}.xlsx"

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    if report_type == 'monthly':
        end_dt = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))
    else:
        end_dt = timezone.make_aware(datetime.combine(sunday, datetime.max.time()))

    ingredients = Ingredient.objects.all().order_by('category', 'name')
    row_num = 2
    for idx, item in enumerate(ingredients, 1):
        # 기초 재고
        prev_stock = InventoryLog.objects.filter(ingredient=item, transaction_date__lt=start_dt).aggregate(
            total=Sum(Case(
                When(log_type='입고', then=F('quantity')),
                When(log_type='출고', then=-F('quantity')),
                When(log_type='폐기', then=-F('quantity')),
                When(log_type='조정', then=F('quantity')),
                default=Value(0),
                output_field=DecimalField()
            ))
        )['total'] or Decimal('0.00')

        # 범위 내 수불
        logs = InventoryLog.objects.filter(ingredient=item, transaction_date__range=(start_dt, end_dt))
        in_qty = logs.filter(log_type='입고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        out_qty = (logs.filter(log_type='출고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')) + \
                  (logs.filter(log_type='폐기').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00'))
        adj_qty = logs.filter(log_type='조정').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0.00')
        curr_stock = prev_stock + in_qty - out_qty + adj_qty

        if prev_stock != 0 or in_qty != 0 or out_qty != 0 or adj_qty != 0:
            ws.cell(row=row_num, column=1, value=row_num-1).border = thin_border
            ws.cell(row=row_num, column=2, value=item.category).border = thin_border
            ws.cell(row=row_num, column=3, value=item.name).border = thin_border
            ws.cell(row=row_num, column=4, value=item.spec).border = thin_border
            ws.cell(row=row_num, column=5, value=item.unit).border = thin_border
            ws.cell(row=row_num, column=6, value=prev_stock).border = thin_border
            ws.cell(row=row_num, column=7, value=in_qty).border = thin_border
            ws.cell(row=row_num, column=8, value=out_qty).border = thin_border
            ws.cell(row=row_num, column=9, value=adj_qty).border = thin_border
            ws.cell(row=row_num, column=10, value=curr_stock).border = thin_border
            ws.cell(row=row_num, column=11, value="").border = thin_border
            row_num += 1

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    wb.save(response)
    return response