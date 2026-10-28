"""
신규 실무 문서 뷰 (procurement 앱)
- doc_purchase_requisition: 급식물품 구입요구서 (A4 세로)
- doc_inspection_log: 급식물품 검수일지 (A4 가로) - 발주예정서 연동
- doc_cooking_instruction: 조리지시서 (A4 세로) - 스마트 단위 환산 적용
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import OrderItem
from .utils import calculate_physical_units, parse_spec_unit_and_qty
from meals.models import DietPlan

WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _parse_date_range(request):
    """GET 파라미터에서 start_date / end_date를 파싱하는 공통 헬퍼."""
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    target_date_str = request.GET.get("date")

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
            end_date = date.today()
    elif target_date_str or start_date_str:
        raw = target_date_str or start_date_str
        try:
            start_date = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
        end_date = start_date
    else:
        start_date = date.today()
        end_date = date.today()

    return start_date, end_date


def doc_purchase_requisition(request):
    """[신규] 급식물품 구입요구서 (실무 양식) - doc_purchase_requisition.html"""
    start_date, end_date = _parse_date_range(request)
    delivery_date = end_date + timedelta(days=1)

    order_items_qs = OrderItem.objects.filter(
        Q(target_date__range=[start_date, end_date]) | Q(purchase_order__created_at__date__range=[start_date, end_date])
    ).select_related("ingredient")

    items_map = defaultdict(lambda: {"ingredient": None, "raw_quantity": 0.0})

    if order_items_qs.exists():
        for item in order_items_qs:
            ing = item.ingredient
            key = (ing.category or "기타", ing.name, ing.id)
            items_map[key]["ingredient"] = ing
            items_map[key]["raw_quantity"] += float(item.required_qty)
    else:
        plans = (
            DietPlan.objects.filter(target_date__range=[start_date, end_date])
            .prefetch_related("diet_menus__menu__recipes__ingredient")
        )
        for plan in plans:
            headcount = plan.headcount or 500
            for dm in plan.diet_menus.all().select_related("menu"):
                for recipe in dm.menu.recipes.all().select_related("ingredient"):
                    ing = recipe.ingredient
                    req_amt = recipe.required_amount or Decimal("0")
                    if req_amt < Decimal("10"):
                        needed = float(req_amt * headcount)
                    else:
                        needed = float(req_amt * headcount / 1000.0)
                    key = (ing.category or "기타", ing.name, ing.id)
                    items_map[key]["ingredient"] = ing
                    items_map[key]["raw_quantity"] += needed

    items = []
    tot_qty_val = 0.0
    tot_amt_val = 0

    if items_map:
        for key, data in items_map.items():
            ing = data["ingredient"]
            raw_qty = data["raw_quantity"]
            category = ing.category or "기타"
            price = getattr(ing, "unit_price", 0) or getattr(ing, "price", 0) or 0

            conv_qty, conv_unit = parse_spec_unit_and_qty(
                spec_str=ing.spec or "",
                total_qty_val=raw_qty,
                unit_str=ing.unit or "",
                category=category,
            )

            amt = int(conv_qty * price)

            items.append({
                "category": category,
                "name": ing.name,
                "spec": ing.spec or "-",
                "unit": conv_unit,
                "quantity": conv_qty,
                "unit_price": f"{price:,}" if price else "-",
                "amount": f"{amt:,}" if price else "-",
                "raw_quantity": conv_qty,
                "raw_amount": amt,
                "remark": ing.description or "-",
            })
            tot_qty_val += float(conv_qty)
            tot_amt_val += amt

        items.sort(key=lambda x: (x["category"], x["name"]))

    total_qty_str = f"{round(tot_qty_val, 1):,}" if tot_qty_val else "0"
    if tot_qty_val == int(tot_qty_val):
        total_qty_str = f"{int(tot_qty_val):,}"

    context = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "target_date": start_date.strftime("%Y-%m-%d"),
        "delivery_date": delivery_date.strftime("%Y-%m-%d"),
        "items": items,
        "total_qty": total_qty_str,
        "total_amount": f"{tot_amt_val:,}" if tot_amt_val else "0",
    }
    return render(request, "docs/doc_purchase_requisition.html", context)



def doc_inspection_log(request):
    """[신규] 급식물품 검수일지 (실무 양식) - 발주예정서 데이터 100% 연동 - doc_inspection_log.html"""
    start_date, end_date = _parse_date_range(request)

    supplier_id = request.GET.get("supplier_id", "").strip()
    User = get_user_model()
    if hasattr(User, "name"):
        suppliers = User.objects.filter(is_superuser=False).order_by("name", "username")
    else:
        suppliers = User.objects.filter(is_superuser=False).order_by("username")
    selected_supplier = None
    supplier_name = "전체"

    if supplier_id:
        try:
            selected_supplier = User.objects.get(id=supplier_id)
            supplier_name = getattr(selected_supplier, "name", "") or selected_supplier.username
        except User.DoesNotExist:
            pass

    # 발주예정서와 동일한 쿼리셋 기반으로 검수일지 구성
    order_items_qs = OrderItem.objects.filter(
        Q(target_date__range=[start_date, end_date]) | Q(purchase_order__created_at__date__range=[start_date, end_date])
    ).select_related("ingredient", "purchase_order__supplier")

    if selected_supplier:
        order_items_qs = order_items_qs.filter(purchase_order__supplier=selected_supplier)

    order_items_qs = order_items_qs.order_by("purchase_order__supplier__username", "ingredient__category", "ingredient__name")

    supplier_map = defaultdict(list)
    for item in order_items_qs:
        sup = item.purchase_order.supplier
        s_name = getattr(sup, "name", "") or sup.username
        category = item.ingredient.category or "기타"
        qty = round(float(item.required_qty), 1)
        if qty == int(qty):
            qty = int(qty)

        # 스마트 단위 환산 적용 (발주예정서와 동일 수량으로 표시)
        ing = item.ingredient
        physical_qty = calculate_physical_units(
            spec_str=ing.spec or "",
            total_qty_val=float(item.required_qty),
            unit_str=ing.unit or "",
            category=ing.category or "",
        )

        supplier_map[s_name].append({
            "category": category,
            "name": ing.name,
            "spec": ing.spec or "-",
            "unit": ing.unit or "kg",
            "quantity": qty,
            "physical_qty": physical_qty,
        })

    supplier_groups = [
        {
            "supplier_name": s_name,
            "items": items_list,
        }
        for s_name, items_list in supplier_map.items()
    ]
    supplier_groups.sort(key=lambda x: x["supplier_name"])

    context = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "target_date": start_date.strftime("%Y-%m-%d"),
        "supplier_name": supplier_name,
        "suppliers": suppliers,
        "selected_supplier": selected_supplier,
        "current_supplier_id": supplier_id,
        "supplier_groups": supplier_groups,
    }
    return render(request, "docs/doc_inspection_log.html", context)


def doc_cooking_instruction(request):
    """[신규] 조리지시서 - 발주예정서 기반, 1인분 컬럼 제거, 스마트 단위 환산 적용."""
    start_date, end_date = _parse_date_range(request)

    plans = (
        DietPlan.objects.filter(target_date__range=[start_date, end_date])
        .prefetch_related("diet_menus__menu__recipes__ingredient")
        .order_by("target_date", "meal_type")
    )

    diet_plans = []
    total_rows = 0

    MEAL_ORDER = {"조식": 1, "중식": 2, "석식": 3}

    for plan in plans:
        date_str = f"{plan.target_date.strftime('%m/%d')} ({WEEKDAYS_KO[plan.target_date.weekday()]})"
        headcount = plan.headcount or 500

        menus_data = []
        plan_rows = 0

        for dm in plan.diet_menus.all().select_related("menu"):
            menu = dm.menu
            recipes = menu.recipes.all().select_related("ingredient")

            ing_list = []
            if recipes.exists():
                for recipe in recipes:
                    ing = recipe.ingredient
                    req_amt = recipe.required_amount or Decimal("0")

                    # 총 필요량 계산 (g 또는 kg 상관없이 통합 처리)
                    ing_cat = ing.category or ""
                    ing_name = ing.name or ""
                    unit = ing.unit if ing.unit else "kg"

                    if req_amt < Decimal("10"):
                        # req_amt가 kg 단위 (소수점 값) → 총 kg
                        total_qty_val = float(req_amt * headcount)
                        total_unit = "kg"
                    else:
                        # req_amt가 g 단위 → 총 g
                        total_qty_val = float(req_amt * headcount / 1000)
                        total_unit = "kg"

                    # 쌀/김치 g → kg 변환
                    if ("쌀" in ing_cat or "김치" in ing_cat or "쌀" in ing_name or "김치" in ing_name) and unit.lower() in ["g", "그램"]:
                        total_unit = "kg"

                    # 스마트 단위 환산
                    physical_qty = calculate_physical_units(
                        spec_str=ing.spec or "",
                        total_qty_val=total_qty_val,
                        unit_str=total_unit,
                        category=ing_cat,
                    )

                    ing_list.append({
                        "name": ing.name,
                        "total_qty": physical_qty,
                        "remark": ing.spec or "-",
                    })
            else:
                ing_list.append({
                    "name": "-",
                    "total_qty": "-",
                    "remark": "-",
                })

            menus_data.append({
                "name": menu.name,
                "rowspan": len(ing_list),
                "ingredients": ing_list,
            })
            plan_rows += len(ing_list)

        diet_plans.append({
            "date_str": date_str,
            "target_date": plan.target_date.strftime("%Y-%m-%d"),
            "meal_type": plan.meal_type,
            "headcount": headcount,
            "rowspan": plan_rows,
            "menus": menus_data,
        })
        total_rows += plan_rows

    # 자동 페이지 분할 (25줄 기준, 인쇄 최적화)
    pages = []
    current_page_plans = []
    current_rows = 0
    PAGE_LIMIT = 25

    for plan in diet_plans:
        if current_rows + plan["rowspan"] > PAGE_LIMIT and current_page_plans:
            pages.append({"page_num": len(pages) + 1, "diet_plans": current_page_plans})
            current_page_plans = [plan]
            current_rows = plan["rowspan"]
        else:
            current_page_plans.append(plan)
            current_rows += plan["rowspan"]

    if current_page_plans:
        pages.append({"page_num": len(pages) + 1, "diet_plans": current_page_plans})

    if not pages:
        pages.append({"page_num": 1, "diet_plans": []})

    context = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "diet_plans": diet_plans,
        "pages": pages,
        "total_pages": len(pages),
        "total_rows": total_rows,
    }
    return render(request, "docs/doc_cooking_instruction.html", context)
