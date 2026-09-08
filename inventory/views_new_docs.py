"""
신규 실무 문서 뷰 (inventory 앱)
- doc_inventory_status: 급식재료 수불현황 (A4 가로, 2줄 양식)
"""
import calendar
from datetime import date, datetime
from decimal import Decimal
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Case, When, F, Value, DecimalField
from .models import Ingredient, InventoryLog


def doc_inventory_status(request):
    """[신규] 급식재료 수불현황 (실무 양식) - doc_inventory_status.html"""
    today = timezone.now().date()

    target_month_str = request.GET.get("month", "").strip()
    if target_month_str:
        try:
            parsed = datetime.strptime(target_month_str, "%Y-%m")
            year = parsed.year
            month = parsed.month
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month_num", today.month))

    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)

    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    next_month_first = end_date + timezone.timedelta(days=1)
    end_dt = timezone.make_aware(datetime.combine(next_month_first, datetime.min.time()))

    ingredients = Ingredient.objects.exclude(name__icontains="테스트").order_by("category", "name")

    inventory_list = []
    total_prev_amount = 0
    total_in_amount = 0
    total_out_amount = 0
    total_curr_amount = 0

    for item in ingredients:
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

        month_logs = InventoryLog.objects.filter(ingredient=item, transaction_date__gte=start_dt, transaction_date__lt=end_dt)
        in_qty = month_logs.filter(log_type='입고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')
        out_qty = (month_logs.filter(log_type='출고').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')) + \
                  (month_logs.filter(log_type='폐기').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0'))
        adj_qty = month_logs.filter(log_type='조정').aggregate(Sum('quantity'))['quantity__sum'] or Decimal('0')

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
        "year": year,
        "month": str(month).zfill(2),
        "target_month": f"{year}-{str(month).zfill(2)}",
        "inventory_list": inventory_list,
        "totals": totals,
    }
    return render(request, "docs/doc_inventory_status.html", context)

