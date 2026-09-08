"""
신규 실무 문서 뷰 (procurement 앱)
- doc_purchase_requisition: 급식물품 구입요구서 (A4 세로)
- doc_inspection_log: 급식물품 검수일지 (A4 가로)
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import OrderItem


def doc_purchase_requisition(request):
    """[신규] 급식물품 구입요구서 (실무 양식) - doc_purchase_requisition.html"""
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
        raw_date_str = target_date_str or start_date_str
        try:
            start_date = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
        end_date = start_date
    else:
        start_date = date.today()
        end_date = date.today()

    delivery_date = end_date + timedelta(days=1)

    order_items_qs = OrderItem.objects.filter(
        Q(target_date__range=[start_date, end_date]) | Q(purchase_order__created_at__date__range=[start_date, end_date])
    ).select_related("ingredient")

    items_map = defaultdict(lambda: {"category": "", "name": "", "spec": "", "unit": "", "quantity": 0.0, "unit_price_val": 0, "remark": ""})

    for item in order_items_qs:
        ing = item.ingredient
        category = ing.category or "기타"
        key = (category, ing.name)
        qty = float(item.required_qty)
        price = getattr(ing, "price", 0) or getattr(ing, "unit_price", 0) or 0
        items_map[key]["category"] = category
        items_map[key]["name"] = ing.name
        items_map[key]["spec"] = ing.spec or "-"
        items_map[key]["unit"] = ing.unit or "kg"
        items_map[key]["quantity"] += qty
        items_map[key]["unit_price_val"] = price
        items_map[key]["remark"] = ing.description or "-"

    items = []
    tot_qty_val = 0.0
    tot_amt_val = 0

    if items_map:
        for key, data in items_map.items():
            qty = round(data["quantity"], 1)
            if qty == int(qty):
                qty = int(qty)
            price = data["unit_price_val"]
            amt = int(qty * price)
            items.append({
                "category": data["category"],
                "name": data["name"],
                "spec": data["spec"],
                "unit": data["unit"],
                "quantity": qty,
                "unit_price": f"{price:,}" if price else "-",
                "amount": f"{amt:,}" if price else "-",
                "remark": data["remark"],
            })
            tot_qty_val += float(qty)
            tot_amt_val += amt
        items.sort(key=lambda x: (x["category"], x["name"]))

    context = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "target_date": start_date.strftime("%Y-%m-%d"),
        "delivery_date": delivery_date.strftime("%Y-%m-%d"),
        "items": items,
        "total_qty": f"{round(tot_qty_val, 1):,}" if tot_qty_val else "",
        "total_amount": f"{tot_amt_val:,}" if tot_amt_val else "",
    }
    return render(request, "docs/doc_purchase_requisition.html", context)


def doc_inspection_log(request):
    """[신규] 급식물품 검수일지 (실무 양식) - doc_inspection_log.html"""
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
        raw_date_str = target_date_str or start_date_str
        try:
            start_date = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
        end_date = start_date
    else:
        start_date = date.today()
        end_date = date.today()

    supplier_id = request.GET.get("supplier_id", "").strip()
    User = get_user_model()
    suppliers = User.objects.filter(is_superuser=False).order_by("username")
    selected_supplier = None
    supplier_name = "전체"

    if supplier_id:
        try:
            selected_supplier = User.objects.get(id=supplier_id)
            supplier_name = getattr(selected_supplier, "name", "") or selected_supplier.username
        except User.DoesNotExist:
            pass

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
        expiry_date = (end_date + timedelta(days=7)).strftime("%Y-%m-%d")

        supplier_map[s_name].append({
            "category": category,
            "name": item.ingredient.name,
            "spec": item.ingredient.spec or "-",
            "unit": item.ingredient.unit or "kg",
            "quantity": qty,
            "expiry": expiry_date,
        })

    supplier_groups = [
        {
            "supplier_name": s_name,
            "items": items_list,
        }
        for s_name, items_list in supplier_map.items()
    ]

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


