import openpyxl  
import re
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages  
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render, get_object_or_404

from .forms import IngredientForm, InventoryLogForm
from .models import Ingredient, InventoryLog

DECIMAL_ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))

def get_ingredient_stock_queryset():
    return (
        Ingredient.objects.all()
        .annotate(
            in_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.IN, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            out_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.OUT, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            waste_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.WASTE, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            adj_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.ADJ, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
        )
        .annotate(
            is_low_stock=Case(
                When(current_stock__lte=F("safe_stock_level"), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("id")
    )

def get_current_stock(ingredient_id):
    ingredient = get_ingredient_stock_queryset().get(pk=ingredient_id)
    return ingredient.current_stock

def ingredient_list(request):
    selected_category = request.GET.get("category", "").strip()
    search_query = request.GET.get("search", "").strip()  

    ingredients = get_ingredient_stock_queryset()

    if selected_category:
        ingredients = ingredients.filter(category=selected_category)
    
    if search_query:
        ingredients = ingredients.filter(name__icontains=search_query)

    categories = (
        Ingredient.objects.exclude(category__isnull=True)
        .exclude(category__exact="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    paginator = Paginator(ingredients, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "selected_category": selected_category,
        "search_query": search_query,  
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
                "식재료명": "name",
                "규격": "spec",
                "단위": "unit",
                "단가": "unit_price",
                "안전재고": "safe_stock_level",
                "대분류": "category",
                "연간예상소요량": "yearly_demand",
                "금액": "total_amount",
            }

            pos = {field: headers.index(name) if name in headers else None 
                   for name, field in col_map.items()}

            if pos["name"] is None:
                messages.error(request, "엑셀 파일에 '식재료명' 컬럼이 반드시 포함되어야 합니다.")
                return redirect("inventory:ingredient_create")

            success_count = 0
            

            for row in sheet.iter_rows(min_row=2, values_only=True):

                def get_val(field):
                    idx = pos.get(field)
                    return row[idx] if idx is not None else None

                name = get_val("name")
                if not name:
                    continue
                
                Ingredient.objects.update_or_create(
                    name=str(name).strip(),
                    defaults={
                        "spec": get_val("spec"),
                        "unit": get_val("unit"),
                        "unit_price": Decimal(str(get_val("unit_price") or 0)),
                        "safe_stock_level": Decimal(str(get_val("safe_stock_level") or 0)),
                        "category": get_val("category"),
                        "yearly_demand": Decimal(str(get_val("yearly_demand") or 0)),
                        "total_amount": Decimal(str(get_val("total_amount") or 0)),
                    }
                )
                success_count += 1
            
            messages.success(request, f"{success_count}건의 식재료가 등록/업데이트되었습니다.")
        except Exception as e:
            messages.error(request, f"파일 처리 중 오류 발생: {e}")
            
        return redirect("inventory:ingredient_list")
    
    return redirect("inventory:ingredient_create")

def inventory_log_create(request):
    if request.method == "POST":
        form = InventoryLogForm(request.POST)
        if form.is_valid():
            ingredient = form.cleaned_data["ingredient"]
            log_type = form.cleaned_data["log_type"]
            quantity = form.cleaned_data["quantity"]

            if log_type in [InventoryLog.LogType.OUT, InventoryLog.LogType.WASTE]:
                current_stock = get_current_stock(ingredient.id)
                if quantity > current_stock:
                    form.add_error(
                        "quantity",
                        f"현재 재고({current_stock})보다 많은 수량은 출고/폐기할 수 없습니다.",
                    )

            if form.is_valid():
                form.save()
                messages.success(request, "입출고 로그가 기록되었습니다.")
                return redirect("inventory:ingredient_list")
        form = InventoryLogForm()

    return render(request, "inventory/inventory_log_form.html", {"form": form})

def ingredient_stock_adjust(request, pk):
    if request.method == "POST":
        ingredient = get_object_or_404(Ingredient, pk=pk)
        try:
            new_stock = Decimal(request.POST.get("new_stock", 0))
            diff = new_stock - ingredient.current_stock
            
            if diff != 0:
                ingredient.current_stock = new_stock
                ingredient.save()
                
                InventoryLog.objects.create(
                    ingredient=ingredient,
                    log_type=InventoryLog.LogType.ADJ,
                    quantity=diff,
                    description="수동 보정"
                )
                messages.success(request, f"{ingredient.name} 재고가 {new_stock}으로 수동 보정되었습니다.")
        except Exception as e:
            messages.error(request, f"오류가 발생했습니다: {e}")
    return redirect("inventory:ingredient_list")

def inventory_ledger(request):
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_date_str = request.GET.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', end_of_week.strftime('%Y-%m-%d'))
    
    try:
        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = start_of_week
        end_date = end_of_week
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
    
    ingredients = Ingredient.objects.all().annotate(
        initial_in=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__lt=start_date) & Q(inventorylog__log_type=InventoryLog.LogType.IN), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        initial_out=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__lt=start_date) & Q(inventorylog__log_type=InventoryLog.LogType.OUT), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        initial_waste=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__lt=start_date) & Q(inventorylog__log_type=InventoryLog.LogType.WASTE), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        initial_adj=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__lt=start_date) & Q(inventorylog__log_type=InventoryLog.LogType.ADJ), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        
        period_in=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__gte=start_date) & Q(inventorylog__transaction_date__lt=end_date + timedelta(days=1)) & Q(inventorylog__log_type=InventoryLog.LogType.IN), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        period_out=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__gte=start_date) & Q(inventorylog__transaction_date__lt=end_date + timedelta(days=1)) & Q(inventorylog__log_type=InventoryLog.LogType.OUT), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        period_waste=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__gte=start_date) & Q(inventorylog__transaction_date__lt=end_date + timedelta(days=1)) & Q(inventorylog__log_type=InventoryLog.LogType.WASTE), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
        period_adj=Coalesce(Sum(Case(When(Q(inventorylog__transaction_date__gte=start_date) & Q(inventorylog__transaction_date__lt=end_date + timedelta(days=1)) & Q(inventorylog__log_type=InventoryLog.LogType.ADJ), then=F("inventorylog__quantity")), default=DECIMAL_ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))), DECIMAL_ZERO),
    ).annotate(
        initial_stock=ExpressionWrapper(F("initial_in") - F("initial_out") - F("initial_waste") + F("initial_adj"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        final_stock=ExpressionWrapper(F("initial_in") - F("initial_out") - F("initial_waste") + F("initial_adj") + F("period_in") - F("period_out") - F("period_waste") + F("period_adj"), output_field=DecimalField(max_digits=12, decimal_places=2))
    ).exclude(
        initial_stock=0,
        period_in=0,
        period_out=0,
        period_waste=0,
        period_adj=0
    ).order_by('category', 'name')

    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'ingredients': ingredients,
    }
    return render(request, 'inventory/inventory_ledger.html', context)