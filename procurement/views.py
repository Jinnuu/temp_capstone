from .money import recorded_amount, review_totals
from config.input_validation import object_by_integer_id
from django.utils.http import content_disposition_header
from config.export_safety import literal_workbook, worksheet_title
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import reduce
import operator

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Case, DateField, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side

from forecasting.models import AttendancePrediction
from forecasting.services.ingredient_calc import get_all_day_requirements
from inventory.models import Ingredient, InventoryLog
from inventory.views import get_ingredient_stock_queryset
from meals.models import DietPlan
from .models import OrderItem, PurchaseOrder


CATEGORY_ORDER = ["밥", "국", "주반찬", "부반찬", "김치", "간식"]

SORT_ORDER = Case(
    *[When(menu__category=cat, then=Value(pos)) for pos, cat in enumerate(CATEGORY_ORDER)],
    default=Value(len(CATEGORY_ORDER)),
    output_field=IntegerField(),
)

MEAL_TO_PREDICTION_KEY = {
    "조식": "breakfast",
    "중식": "lunch",
    "석식": "dinner",
}


def to_decimal(value, default="0"):
    try:
        result = Decimal(str(value).replace(",", "").strip())
        return result if result.is_finite() else Decimal(default)
    except (ValueError, TypeError, ArithmeticError):
        return Decimal(default)


def get_or_create_dummy_user(request):
    if request.user.is_authenticated:
        return request.user

    User = get_user_model()
    user = User.objects.first()

    if not user:
        user = User.objects.create_user(username="admin_dummy", password="dummy_password")

    return user


def get_current_stock(ingredient):
    """InventoryLog 기준 현재고 계산. 기존 데이터가 영문/한글 로그값을 섞어 쓰는 경우까지 방어."""
    in_sum = (
        InventoryLog.objects.filter(
            ingredient=ingredient,
            log_type__in=[InventoryLog.LogType.IN, "IN", "입고", "1"],
        ).aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    out_sum = (
        InventoryLog.objects.filter(
            ingredient=ingredient,
            log_type__in=[InventoryLog.LogType.OUT, "OUT", "출고", "2"],
        ).aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    waste_sum = (
        InventoryLog.objects.filter(
            ingredient=ingredient,
            log_type__in=[InventoryLog.LogType.WASTE, "WASTE", "폐기", "3"],
        ).aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    adj_sum = (
        InventoryLog.objects.filter(
            ingredient=ingredient,
            log_type__in=[InventoryLog.LogType.ADJ, "ADJ", "조정", "4"],
        ).aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )

    return to_decimal(in_sum) - to_decimal(out_sum) - to_decimal(waste_sum) + to_decimal(adj_sum)


def get_serving_count(plan):
    """AI is reference information; only nutritionists may confirm operational counts."""
    if plan.final_headcount is not None:
        return plan.final_headcount, "영양사 최종 확정"
    return int(plan.headcount or 0), "미확정 · 직접 예상 참고값"


@transaction.atomic
def order_create(request):
    """간편주문 생성. GET 파라미터 또는 날짜 기준 부족분을 수량에 자동 채운다."""
    if request.method == "POST":
        from .workflow import create_manual_plan
        from django.core.exceptions import ValidationError
        try:
            ids = request.POST.getlist("ingredient_id[]")
            amounts = request.POST.getlist("quantity[]")
            if len(ids) != len(amounts):
                raise ValidationError("품목과 수량을 확인하세요.")
            selected_date = date.fromisoformat(request.POST.get("target_date") or date.today().isoformat())
            plan = create_manual_plan(zip(ids, amounts), selected_date, request.user, request.POST.get("request_key"))
            return redirect("procurement:workflow_plan", pk=plan.pk)
        except (ValidationError, ValueError, TypeError) as exc:
            messages.error(request, " / ".join(exc.messages) if isinstance(exc, ValidationError) else "날짜 또는 요청 식별자가 올바르지 않습니다.")
            return redirect("procurement:order_create")

    items_names = request.GET.getlist("items")
    amounts = request.GET.getlist("amounts")
    target_date = request.GET.get("target_date")
    shortage_map = {}

    # Explicit name/amount pairs take priority, including numeric ingredient names.
    if items_names and amounts:
        shortage_map = dict(zip(items_names, amounts))
    elif items_names:
        raw_ids = [part.strip() for item in items_names for part in item.split(",")]
        ingredient_ids = [int(part) for part in raw_ids if part.isdigit()]
        for ing in get_ingredient_stock_queryset().filter(pk__in=ingredient_ids):
            shortage = ing.safe_stock_level - ing.calc_stock
            if shortage > 0:
                shortage_map[ing.name] = str(shortage.quantize(Decimal("0.01")))
    elif target_date:
        requirements = get_all_day_requirements(target_date)
        for name, data in requirements.get("items", {}).items():
            order_amount = to_decimal(data.get("order_amount", 0))
            if order_amount > 0:
                shortage_map[name] = str(order_amount)

    ingredients = Ingredient.objects.exclude(name__icontains="테스트").order_by("name")
    categories = (
        Ingredient.objects.exclude(name__icontains="테스트")
        .exclude(category__isnull=True)
        .exclude(category__exact="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(
        request,
        "procurement/order_create.html",
        {
            "ingredients": ingredients,
            "categories": categories,
            "shortage_map": shortage_map,
            "request_key": uuid.uuid4(),
            "target_date": target_date or date.today().isoformat(),
        },
    )


def order_list(request):
    orders = PurchaseOrder.objects.all().order_by("-created_at")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status_filter = request.GET.get("status")

    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)

    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    if status_filter and status_filter != "전체":
        orders = orders.filter(status=status_filter)

    orders_by_supplier = defaultdict(list)

    for order in orders:
        orders_by_supplier[order.supplier].append(order)

    supplier_groups = []

    for supplier, s_orders in orders_by_supplier.items():
        supplier_groups.append(
            {
                "supplier": supplier,
                "orders": s_orders,
            }
        )

    supplier_groups.sort(key=lambda x: x["supplier"].name or x["supplier"].username)

    return render(
        request,
        "procurement/order_list.html",
        {
            "orders": orders,
            "supplier_groups": supplier_groups,
            "start_date": start_date,
            "end_date": end_date,
            "status_filter": status_filter,
        },
    )


def order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)

    meal_order = Case(
        When(meal_type="조식", then=Value(1)),
        When(meal_type="중식", then=Value(2)),
        When(meal_type="석식", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    items = order.items.select_related("ingredient").order_by(
        "target_date",
        meal_order,
        "ingredient__name",
    )

    monetary_review = review_totals(order.items.all())
    subtotal = monetary_review["recorded_total"]
    vat = monetary_review["tax_amount"]
    total = monetary_review["payable_amount"]

    return render(
        request,
        "procurement/order_detail.html",
        {
            "order": order,
            "items": items,
            "subtotal": subtotal,
            "tax_note": "확인 필요 (세금 기준 미등록)",
            "vat": vat,
            "total": total,
        },
    )


@transaction.atomic
def order_status_update(request, pk):
    """Legacy status control cannot bypass inspection or create stock receipts."""
    if request.method == "POST":
        order = get_object_or_404(PurchaseOrder.objects.select_for_update(), pk=pk)
        status = request.POST.get("status")
        if order.status in ["완료", "배송완료"]:
            messages.info(request, "완료된 발주의 상태·입고 이력은 변경하지 않습니다.")
        elif status in ["완료", "배송완료", "배송중"]:
            messages.error(request, "품목별 검수 기록에서 실제 합격량을 입고 처리하세요.")
            return redirect("procurement:workflow_inspections")
        elif status in ["대기", "승인"]:
            order.status = status
            order.save(update_fields=["status"])
            messages.success(request, "발주 상태를 저장했습니다.")
        else:
            messages.error(request, "유효하지 않은 상태입니다.")
    return redirect("procurement:order_detail", pk=pk)


@transaction.atomic
def order_from_mealplan(request):
    """식단, 예측 식수, 레시피, 현재고, 안전재고를 기준으로 부족 수량을 자동 계산해 발주한다."""
    if request.method == "POST":
        from .workflow import create_plan
        from django.core.exceptions import ValidationError
        try:
            start = date.fromisoformat(request.POST.get("order_start_date") or request.GET.get("start_date", ""))
            end = date.fromisoformat(request.POST.get("order_end_date") or request.GET.get("end_date") or str(start))
            plan = create_plan(start, end, request.user, request.POST.get("request_key"), request.POST.getlist("days") or None)
            messages.info(request, "포장규격 환산 결과를 확인하고 업체별 구매발주서를 확정하세요.")
            return redirect("procurement:workflow_plan", pk=plan.pk)
        except (ValidationError, ValueError, TypeError) as exc:
            messages.error(request, " / ".join(exc.messages) if isinstance(exc, ValidationError) else "발주일과 요청 식별자를 확인하세요.")
            return redirect("procurement:workflow_preview")

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    DAY_CHOICES = [
        ("0", "월"),
        ("1", "화"),
        ("2", "수"),
        ("3", "목"),
        ("4", "금"),
        ("5", "토"),
        ("6", "일"),
    ]

    if "start_date" in request.GET:
        selected_days = request.GET.getlist("days")
    else:
        selected_days = ["0", "1", "2", "3", "4", "5", "6"]

    today = date.today()

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today
    else:
        start_date = today

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            end_date = start_date
    else:
        end_date = start_date

    if end_date < start_date:
        end_date = start_date

    meal_order = Case(
        When(meal_type=DietPlan.MealType.BREAKFAST, then=Value(1)),
        When(meal_type=DietPlan.MealType.LUNCH, then=Value(2)),
        When(meal_type=DietPlan.MealType.DINNER, then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]

    stock_balance = {
        ingredient.id: get_current_stock(ingredient)
        for ingredient in Ingredient.objects.exclude(name__icontains="테스트")
    }

    initial_stock_balance = stock_balance.copy()
    grouped_orders = []

    curr_date = start_date
    while curr_date <= end_date:
        if curr_date.weekday() in (5, 6):
            curr_date += timedelta(days=1)
            continue

        if str(curr_date.weekday()) not in selected_days:
            curr_date += timedelta(days=1)
            continue

        order_date = curr_date
        next_day = order_date + timedelta(days=1)

        if order_date.weekday() == 4:  # 금요일
            query = (
                Q(target_date=order_date, meal_type=DietPlan.MealType.DINNER)
                | Q(target_date=order_date + timedelta(days=1))  # 토요일 전체
                | Q(target_date=order_date + timedelta(days=2))  # 일요일 전체
                | Q(target_date=order_date + timedelta(days=3), meal_type__in=[DietPlan.MealType.BREAKFAST, DietPlan.MealType.LUNCH])  # 차주 월요일
            )
        else:  # 월, 화, 수, 목
            query = (
                Q(target_date=order_date, meal_type=DietPlan.MealType.DINNER)
                | Q(target_date=next_day, meal_type__in=[DietPlan.MealType.BREAKFAST, DietPlan.MealType.LUNCH])
            )

        plans = (
            DietPlan.objects.filter(query)
            .distinct()
            .prefetch_related("diet_menus__menu__recipes__ingredient__supplier")
            .order_by("target_date", meal_order)
        )

        date_plans = []
        for plan in plans:
            serving_count, serving_source = get_serving_count(plan)

            dt = plan.target_date
            dt_str = f"{dt.strftime('%d일')}({WEEKDAYS_KO[dt.weekday()]})"
            meal_type_display = f"{dt_str} {plan.meal_type}"

            plan_item = {
                "target_date": plan.target_date,
                "meal_type": plan.meal_type,
                "meal_type_display": meal_type_display,
                "headcount": plan.headcount,
                "serving_count": serving_count,
                "serving_source": serving_source,
                "menus": [],
            }

            sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by(SORT_ORDER)

            for diet_menu in sorted_diet_menus:
                menu = diet_menu.menu
                menu_item = {
                    "id": menu.id,
                    "name": menu.name,
                    "ingredients": [],
                }

                for recipe in menu.recipes.all():
                    ing = recipe.ingredient
                    current_before = stock_balance.get(ing.id, Decimal("0"))
                    from .workflow import convert
                    required_per_person = convert(recipe.required_amount, recipe.unit or ing.unit, ing.unit)
                    needed_qty = to_decimal(serving_count) * required_per_person
                    safe_stock = to_decimal(ing.safe_stock_level)
                    shortage_qty = needed_qty + safe_stock - current_before
                    order_qty = shortage_qty if shortage_qty > 0 and needed_qty > 0 else Decimal("0")

                    # 현재 끼니 소비량만큼 재고를 차감한다. 음수는 0으로 고정한다.
                    stock_balance[ing.id] = current_before + order_qty - needed_qty

                    menu_item["ingredients"].append(
                        {
                            "id": ing.id,
                            "name": ing.name,
                            "unit": ing.unit,
                            "price": ing.unit_price,
                            "category": ing.category,
                            "spec": ing.spec,
                            "description": ing.description,
                            "supplier_name": ing.supplier.name if ing.supplier else "미정",
                            "current_stock": round(current_before, 2),
                            "initial_stock": round(initial_stock_balance.get(ing.id, Decimal("0")), 2),
                            "safe_stock": round(safe_stock, 2),
                            "needed_qty": round(needed_qty, 2),
                            "order_qty": round(order_qty, 2),
                            "required_per_person": float(required_per_person),
                        }
                    )

                plan_item["menus"].append(menu_item)

            date_plans.append(plan_item)

        if date_plans:
            order_date_display = f"{curr_date.strftime('%Y년 %m월 %d일')} ({WEEKDAYS_KO[curr_date.weekday()]})"
            grouped_orders.append({
                "order_date": curr_date,
                "order_date_display": order_date_display,
                "plans": date_plans,
            })

        curr_date += timedelta(days=1)

    return render(
        request,
        "procurement/order_from_mealplan.html",
        {
            "start_date": start_date,
            "end_date": end_date,
            "grouped_orders": grouped_orders,
            "request_key": uuid.uuid4(),
            "all_ingredients": Ingredient.objects.exclude(name__icontains="테스트").order_by("name"),
            "selected_days": selected_days,
            "day_choices": DAY_CHOICES,
        },
    )


def get_monday_sunday_range(date_str):
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6)
    return target_date, monday, sunday


def weekly_procurement_report(request):
    target_date, monday, sunday = get_monday_sunday_range(request.GET.get("date"))

    # Use Coalesce to fallback to purchase_order__created_at__date if target_date is NULL
    order_items = OrderItem.objects.annotate(
        display_date=Coalesce(F("target_date"), Cast(F("purchase_order__created_at"), DateField()))
    ).filter(
        display_date__range=[monday, sunday]
    ).select_related("ingredient", "purchase_order__supplier").order_by("display_date", "ingredient__name")

    # Group by date
    analysis_data = defaultdict(list)
    for item in order_items:
        analysis_data[item.display_date].append(item)

    report_data = [
        {"date": dt, "items": analysis_data[dt]}
        for dt in sorted(analysis_data.keys())
    ]

    context = {
        "report_data": report_data,
        "monday": monday,
        "sunday": sunday,
        "target_date": target_date,
        "prev_week_date": (monday - timedelta(days=7)).isoformat(),
        "next_week_date": (monday + timedelta(days=7)).isoformat(),
    }
    return render(request, "docs/weekly_procurement_report.html", context)


def get_vendor_procurement_data(start_date, end_date, supplier=None, order=None):
    """New snapshots use order dates; historical meal rows keep procurement-day grouping."""
    base = OrderItem.objects.select_related('ingredient', 'purchase_order__supplier', 'purchase_order__workflow_plan')
    if supplier:
        base = base.filter(purchase_order__supplier=supplier)
    if order is not None:
        base=base.filter(purchase_order=order)
    groups=[]; seen=set(); totals=defaultdict(lambda: Decimal('0')); amount=0; count=0
    day=start_date
    while day<=end_date:
        direct = Q(target_date=day) & (Q(purchase_order__workflow_plan__isnull=False) | Q(meal_type__isnull=True) | Q(meal_type=''))
        direct |= Q(target_date__isnull=True, purchase_order__created_at__date=day)
        legacy = Q(pk__in=[])
        if day.weekday()<5:
            last=day+timedelta(days=3 if day.weekday()==4 else 1)
            legacy = Q(target_date=day, meal_type='석식') | Q(target_date=last, meal_type__in=['조식','중식'])
            if day.weekday()==4:
                legacy |= Q(target_date__gt=day, target_date__lt=last)
            legacy &= Q(purchase_order__workflow_plan__isnull=True, meal_type__in=['조식','중식','석식'])
        items=list(base.filter(direct | legacy).exclude(pk__in=seen).order_by('target_date','meal_type','ingredient__name'))
        for item in items:
            seen.add(item.pk)
            item.meal_date_display=(item.target_date.strftime('%m/%d') if item.target_date else day.strftime('%m/%d')) + (' '+item.meal_type if item.meal_type else '')
            totals[item.purchase_unit]+=item.purchase_quantity
            amount+=recorded_amount(item);count+=1
        if items:
            groups.append({'date':day,'order_date':day,'order_date_display':str(day),'items':items})
        day+=timedelta(days=1)
    return {'grouped_orders':groups,'report_data':groups,'total_item_count':count,
        'total_order_qty':' / '.join(f'{qty.normalize():f} {unit}' for unit,qty in sorted(totals.items())) or '0',
        'total_amount':amount,'subtotal':None,'vat':None}

def vendor_procurement_report(request):
    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()
    supplier_id = request.GET.get("supplier_id", "").strip()

    if supplier_id in ("", "None", "none"):
        supplier_id = ""

    target_date, default_monday, default_sunday = get_monday_sunday_range(request.GET.get("date"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else default_monday
    except ValueError:
        start_date = default_monday

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else default_sunday
    except ValueError:
        end_date = default_sunday

    user_model = get_user_model()
    supplier_qs = user_model.objects.filter(is_superuser=False).filter(
        Q(purchase_orders__isnull=False) | Q(supplied_ingredients__isnull=False)
    ).distinct()

    if hasattr(user_model, "name"):
        suppliers = supplier_qs.order_by("name", "username")
    else:
        suppliers = supplier_qs.order_by("username")
    selected_supplier = None

    if supplier_id:
        selected_supplier = object_by_integer_id(get_user_model(), supplier_id)

    proc_data = get_vendor_procurement_data(start_date, end_date, selected_supplier)

    context = {
        "suppliers": suppliers,
        "selected_supplier": selected_supplier,
        "current_supplier_id": supplier_id,
        "report_data": proc_data["report_data"],
        "grouped_orders": proc_data["grouped_orders"],
        "start_date": start_date,
        "end_date": end_date,
        "monday": start_date,
        "sunday": end_date,
        "target_date": target_date,
        "total_item_count": proc_data["total_item_count"],
        "total_order_qty": proc_data["total_order_qty"],
        "total_amount": proc_data["total_amount"],
        "subtotal": proc_data["subtotal"],
        "vat": proc_data["vat"],
    }
    return render(request, "docs/vendor_procurement_report.html", context)


def export_weekly_procurement_excel(request):
    _, monday, sunday = get_monday_sunday_range(request.GET.get("date"))
    items = OrderItem.objects.annotate(
        display_date=Coalesce(F("target_date"), Cast(F("purchase_order__created_at"), DateField()))
    ).filter(
        display_date__range=[monday, sunday]
    ).select_related("ingredient", "purchase_order__supplier").order_by("display_date", "ingredient__name")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "주간발주서"

    headers = ["No", "식단일", "분류", "식재료명", "규격", "단위", "단가", "기준량(재고 단위)", "발주량", "금액", "공급처", "주문일자"]
    ws.append(headers)

    for i, item in enumerate(items, 1):
        ws.append([
            i,
            item.display_date.strftime("%Y-%m-%d") if item.display_date else "-",
            item.ingredient.category or "-",
            item.ingredient.name,
            item.purchase_spec or "-",
            item.purchase_unit,
            float(item.purchase_price),
            f"{item.required_qty} {item.ingredient.unit}",
            float(item.purchase_quantity),
            recorded_amount(item),
            item.purchase_order.supplier.name or item.purchase_order.supplier.username,
            item.purchase_order.created_at.strftime("%Y-%m-%d")
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="weekly_procurement_{monday}.xlsx"'
    literal_workbook(wb)
    wb.save(response)
    return response


def export_vendor_procurement_excel(request):
    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()
    supplier_id = request.GET.get("supplier_id", "").strip()

    if supplier_id in ("", "None", "none"):
        supplier_id = ""

    _, default_monday, default_sunday = get_monday_sunday_range(request.GET.get("date"))

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else default_monday
    except ValueError:
        start_date = default_monday

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else default_sunday
    except ValueError:
        end_date = default_sunday

    supplier = None
    if supplier_id:
        supplier = object_by_integer_id(get_user_model(), supplier_id)
        supplier_title = supplier.name or supplier.username
    else:
        supplier_title = "전체납품업체통합"

    proc_data = get_vendor_procurement_data(start_date, end_date, supplier, order=getattr(request, 'snp_portal_order', None))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = worksheet_title(f"구매발주서_{supplier_title}")

    headers = ["No", "식단일", "공급처", "분류", "식재료명", "규격", "단위", "단가", "기준량(재고 단위)", "발주량", "금액", "주문일자"]
    ws.append(headers)

    item_idx = 1
    for date_group in proc_data["grouped_orders"]:
        order_date_str = date_group["order_date"].strftime("%Y-%m-%d")
        for item in date_group["items"]:
            supplier_name = "-"
            if item.purchase_order and item.purchase_order.supplier:
                supplier_name = getattr(item.purchase_order.supplier, "name", None) or item.purchase_order.supplier.username

            ws.append([
                item_idx,
                item.meal_date_display,
                supplier_name,
                item.ingredient.category or "-",
                item.ingredient.name,
                item.purchase_spec or "-",
                item.purchase_unit,
                float(item.purchase_price),
                f"{item.required_qty} {item.ingredient.unit}",
                float(item.purchase_quantity),
                recorded_amount(item),
                order_date_str
            ])
            item_idx += 1

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"vendor_procurement_{supplier_title}_{start_date}.xlsx"
    response["Content-Disposition"] = content_disposition_header(True, filename)
    literal_workbook(wb)
    wb.save(response)
    return response


def daily_inspection_report(request):
    date_str = request.GET.get("date")
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    supplier_id = request.GET.get("supplier_id")
    suppliers = get_user_model().objects.filter(purchase_orders__isnull=False).distinct()
    selected_supplier = None
    report_items = []

    order_items = OrderItem.objects.annotate(
        display_date=Coalesce(F("target_date"), Cast(F("purchase_order__created_at"), DateField()))
    ).filter(
        display_date=target_date
    ).select_related("ingredient", "purchase_order__supplier").order_by("ingredient__category", "ingredient__name")

    if supplier_id:
        selected_supplier = object_by_integer_id(get_user_model(), supplier_id)
        order_items = order_items.filter(purchase_order__supplier=selected_supplier)

    report_items = order_items
    total_amount = sum((recorded_amount(item) for item in report_items), Decimal('0'))

    context = {
        "target_date": target_date,
        "prev_day_date": (target_date - timedelta(days=1)).isoformat(),
        "next_day_date": (target_date + timedelta(days=1)).isoformat(),
        "suppliers": suppliers,
        "selected_supplier": selected_supplier,
        "current_supplier_id": supplier_id,
        "report_items": report_items,
        "total_amount": total_amount,
    }
    return render(request, "docs/daily_inspection_report.html", context)


def export_daily_inspection_excel(request):
    date_str = request.GET.get("date")
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    supplier_id = request.GET.get("supplier_id")
    
    order_items = OrderItem.objects.annotate(
        display_date=Coalesce(F("target_date"), Cast(F("purchase_order__created_at"), DateField()))
    ).filter(
        display_date=target_date
    ).select_related("ingredient", "purchase_order__supplier").order_by("ingredient__category", "ingredient__name")

    filename_suffix = "전체"
    selected_supplier_name = "전체"
    if supplier_id:
        supplier = object_by_integer_id(get_user_model(), supplier_id)
        order_items = order_items.filter(purchase_order__supplier=supplier)
        selected_supplier_name = supplier.name or supplier.username
        filename_suffix = selected_supplier_name

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "검수서_주문"

    # Set Column Widths
    col_widths = [10, 25, 15, 8, 10, 15, 10, 10, 8, 8, 12, 8, 10]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    # Title
    ws.merge_cells("A1:I2")
    ws["A1"] = "검 수 서 (주 문)"
    ws["A1"].font = Font(size=20, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    # Approval Table (Top Right)
    # Row 1: Label
    ws.merge_cells("J1:J2")
    ws["J1"] = "결재"
    ws["K1"] = "담당"
    ws["L1"] = "팀장"
    ws["M1"] = "점장"
    # Row 2: Empty for signatures
    # (J1:J2 merged carries the label)
    
    # Style Approval Label
    for cell_coord in ["J1", "K1", "L1", "M1"]:
        ws[cell_coord].alignment = Alignment(horizontal="center", vertical="center")
        ws[cell_coord].font = Font(bold=True)
        ws[cell_coord].border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
        ws[cell_coord].fill = openpyxl.styles.PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    # Style Approval Content Boxes (Below)
    for row_idx in [2]:
        for col_letter in ["K", "L", "M"]:
            cell = ws[f"{col_letter}{row_idx}"]
            cell.border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    ws.row_dimensions[2].height = 40

    # Meta Info
    ws["A3"] = f"납품업체 : {selected_supplier_name}"
    ws["A4"] = "사업장 : S&P 급식소"
    ws["A5"] = f"입고일자 : {target_date}"
    for row in [3, 4, 5]:
        ws[f"A{row}"].font = Font(bold=True)

    # Table Headers (Double Row)
    # Row 6: Main Headers
    ws.merge_cells("A6:A7")
    ws["A6"] = "구분"
    ws.merge_cells("B6:B7")
    ws["B6"] = "품명"
    ws.merge_cells("C6:C7")
    ws["C6"] = "규격"
    ws.merge_cells("D6:D7")
    ws["D6"] = "단위"
    ws.merge_cells("E6:E7")
    ws["E6"] = "주문량"
    ws.merge_cells("F6:F7")
    ws["F6"] = "주문비고"
    ws.merge_cells("G6:G7")
    ws["G6"] = "원산지"
    
    ws.merge_cells("H6:M6")
    ws["H6"] = "검수 결과 (현장 수기 작성용)"
    
    # Row 7: Sub Headers
    ws["H7"] = "검수량"
    ws["I7"] = "포장"
    ws["J7"] = "품온"
    ws["K7"] = "소비기한"
    ws["L7"] = "품질"
    ws["M7"] = "조치"

    # Style Headers
    header_font = Font(color="FFFFFF", bold=True)
    header_fill = openpyxl.styles.PatternFill(start_color="444444", end_color="444444", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    header_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))

    for row_idx in [6, 7]:
        for col_idx in range(1, 14):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = header_border

    # Data Rows
    current_row = 8
    for item in order_items:
        ws.cell(row=current_row, column=1, value=item.ingredient.category or "-")
        ws.cell(row=current_row, column=2, value=item.ingredient.name)
        ws.cell(row=current_row, column=3, value=item.ingredient.spec or "-")
        ws.cell(row=current_row, column=4, value=item.ingredient.unit)
        ws.cell(row=current_row, column=5, value=float(item.required_qty if item.package_quantity is not None else item.missing_qty))
        ws.cell(row=current_row, column=6, value="-") # 주문비고
        ws.cell(row=current_row, column=7, value="-") # 원산지
        # H to M are blank
        for col_idx in range(1, 14):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.border = header_border
            cell.alignment = Alignment(horizontal="center")
        current_row += 1

    # Fill empty rows up to 20 if needed
    while current_row < 25:
        for col_idx in range(1, 14):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.border = header_border
        current_row += 1

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"daily_inspection_{target_date}_{filename_suffix}.xlsx"
    response["Content-Disposition"] = content_disposition_header(True, filename)
    literal_workbook(wb)
    wb.save(response)
    return response
