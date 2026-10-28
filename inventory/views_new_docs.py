"""
신규 실무 문서 뷰 (inventory 앱)
- doc_inventory_status: 급식재료 수불현황 (A4 가로, 2줄 양식)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Case, When, F, Value, DecimalField, OuterRef, Exists
from .models import Ingredient, InventoryLog


def doc_inventory_status(request):
    """[신규] 급식재료 수불현황 (기간 조회, 실사용 품목 필터링) - doc_inventory_status.html"""
    today = timezone.now().date()

    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date(today.year, today.month, 1)
    else:
        start_date = date(today.year, today.month, 1)

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    if end_date < start_date:
        end_date = start_date

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    )

    # 기간 내 InventoryLog가 1건이라도 있는 Ingredient만 필터링 (실사용 품목 필터)
    active_logs_subquery = InventoryLog.objects.filter(
        ingredient=OuterRef("pk"),
        transaction_date__gte=start_dt,
        transaction_date__lt=end_dt,
    )

    ingredients = (
        Ingredient.objects.exclude(name__icontains="테스트")
        .annotate(has_activity=Exists(active_logs_subquery))
        .filter(has_activity=True)
        .order_by("category", "name")
    )

    inventory_list = []
    total_prev_amount = 0
    total_in_amount = 0
    total_out_amount = 0
    total_curr_amount = 0

    for item in ingredients:
        # 기초 재고 (start_date 이전 누적)
        prev_logs = InventoryLog.objects.filter(ingredient=item, transaction_date__lt=start_dt)
        prev_qty = prev_logs.aggregate(
            total=Sum(Case(
                When(log_type='입고', then=F('quantity')),
                When(log_type='출고', then=-F('quantity')),
                When(log_type='폐기', then=-F('quantity')),
                When(log_type='조정', then=F('quantity')),
                default=Value(0),
                output_field=DecimalField()
            ))
        )['total'] or Decimal('0')

        # 기간 내 수불 내역
        period_logs = InventoryLog.objects.filter(
            ingredient=item,
            transaction_date__gte=start_dt,
            transaction_date__lt=end_dt,
        )
        in_qty = period_logs.filter(log_type='입고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')
        out_qty = (
            (period_logs.filter(log_type='출고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')) +
            (period_logs.filter(log_type='폐기').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0'))
        )
        adj_qty = period_logs.filter(log_type='조정').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')

        curr_qty = prev_qty + in_qty - out_qty + adj_qty

        unit_price = item.unit_price or 0
        prev_amount = int(prev_qty * unit_price)
        in_amount = int(in_qty * unit_price)
        out_amount = int(out_qty * unit_price)
        curr_amount = int(curr_qty * unit_price)

        total_prev_amount += prev_amount
        total_in_amount += in_amount
        total_out_amount += out_amount
        total_curr_amount += curr_amount

        remark = "보충필요" if (curr_qty < item.safe_stock_level) else "정상재고"

        inventory_list.append({
            "category": item.category or "기타",
            "name": item.name,
            "spec": item.spec or "-",
            "unit": item.unit,
            "prev_qty": float(prev_qty),
            "in_qty": float(in_qty),
            "out_qty": float(out_qty),
            "adj_qty": float(adj_qty),
            "curr_qty": float(curr_qty),
            "unit_price": unit_price,
            "safe_stock": float(item.safe_stock_level),
            "prev_amount": prev_amount,
            "in_amount": in_amount,
            "out_amount": out_amount,
            "curr_amount": curr_amount,
            "remark": remark,
        })

    totals = {
        "prev_amount": total_prev_amount,
        "in_amount": total_in_amount,
        "out_amount": total_out_amount,
        "curr_amount": total_curr_amount,
    }

    context = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "inventory_list": inventory_list,
        "totals": totals,
        "item_count": len(inventory_list),
    }
    return render(request, "docs/doc_inventory_status.html", context)
