"""Team document layouts using preserved workflow semantics."""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from .models import OrderItem


@login_required
def monthly_settlement_view(request):
    """
    [9단계] 월말 정산 (총 식자재 소요량 및 금액 정산)
    - 특정 월(Month: YYYY-MM) 기준 한 달간의 총 식자재 발주 소요량과 총 청구 금액을 발주처별/대분류별로 합산(Aggregation)
    """
    import calendar
    today = date.today()
    month_str = request.GET.get("month", "").strip()

    if month_str:
        try:
            parsed = datetime.strptime(month_str, "%Y-%m").date()
            year = parsed.year
            month = parsed.month
        except ValueError:
            return HttpResponse("올바른 연월을 입력하세요.", status=400)
    else:
        year = today.year
        month = today.month

    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)

    target_month_display = f"{year}년 {month:02d}월"
    target_month_str = f"{year}-{month:02d}"

    # Filter OrderItems for the target month
    order_items_qs = OrderItem.objects.filter(
        Q(target_date__range=[start_date, end_date]) | Q(target_date__isnull=True, purchase_order__created_at__date__range=[start_date, end_date])
    ).select_related("ingredient", "purchase_order__supplier")

    # Aggregation 1: By Supplier (발주처별)
    supplier_agg = defaultdict(lambda: {
        "supplier_name": "",
        "item_count": 0,
        "total_qty": defaultdict(Decimal),
        "total_amount": 0,
    })

    # Aggregation 2: By Category (대분류별)
    category_agg = defaultdict(lambda: {
        "category_name": "",
        "item_count": 0,
        "total_qty": defaultdict(Decimal),
        "total_amount": 0,
    })

    # Detailed item breakdown list
    item_details = []
    grand_total_qty = defaultdict(Decimal)
    grand_total_amount = 0

    for item in order_items_qs:
        supplier_user = item.purchase_order.supplier
        sup_name = getattr(supplier_user, "name", "") or supplier_user.username
        category = item.ingredient.category or "기타"
        qty = item.required_qty
        unit_price = item.order_unit_price or item.ingredient.unit_price or 0
        amount = item.estimated_price
        unit_price = Decimal(amount) / qty if qty else Decimal("0")

        # Supplier agg
        supplier_agg[sup_name]["supplier_name"] = sup_name
        supplier_agg[sup_name]["item_count"] += 1
        supplier_agg[sup_name]["total_qty"][item.ingredient.unit] += qty
        supplier_agg[sup_name]["total_amount"] += amount

        # Category agg
        category_agg[category]["category_name"] = category
        category_agg[category]["item_count"] += 1
        category_agg[category]["total_qty"][item.ingredient.unit] += qty
        category_agg[category]["total_amount"] += amount

        grand_total_qty[item.ingredient.unit] += qty
        grand_total_amount += amount

        item_details.append({
            "supplier_name": sup_name,
            "category": category,
            "ingredient_name": item.ingredient.name,
            "spec": item.ingredient.spec or "-",
            "unit": item.ingredient.unit or "kg",
            "unit_price": unit_price,
            "quantity": round(qty, 2),
            "amount": amount,
            "target_date": item.target_date.strftime("%Y-%m-%d") if item.target_date else item.purchase_order.created_at.strftime("%Y-%m-%d"),
        })

    supplier_summary = sorted(supplier_agg.values(), key=lambda x: x["total_amount"], reverse=True)
    category_summary = sorted(category_agg.values(), key=lambda x: x["total_amount"], reverse=True)
    item_details.sort(key=lambda x: (x["supplier_name"], x["category"], x["ingredient_name"]))

    def quantities(values):
        return ' / '.join(f'{amount.normalize():f} {unit}' for unit, amount in sorted(values.items())) or '0'
    for summary in supplier_summary + category_summary:
        summary['total_qty'] = quantities(summary['total_qty'])
    # Tax-inclusive prices, exemptions and invoicing are not specified by existing data.
    subtotal = vat = '확인 필요 (세금 기준 미등록)'

    context = {
        "year": year,
        "month": f"{month:02d}",
        "target_month": target_month_str,
        "target_month_display": target_month_display,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "supplier_summary": supplier_summary,
        "category_summary": category_summary,
        "item_details": item_details,
        "grand_total_qty": quantities(grand_total_qty),
        "grand_total_amount": grand_total_amount,
        "subtotal": subtotal,
        "vat": vat,
    }
    return render(request, "docs/doc_monthly_settlement.html", context)


@login_required
def doc_cooking_instruction(request):
    from meals.models import DietPlan, CookingInstruction
    from meals.cooking import cooking_sheet, display_quantity
    from django.urls import reverse
    from django.utils import timezone
    try:
        start = date.fromisoformat(request.GET.get('start_date') or request.GET.get('date') or str(timezone.localdate()))
        end = date.fromisoformat(request.GET.get('end_date') or str(start))
        if end < start or (end-start).days > 62:
            raise ValueError()
    except ValueError:
        return HttpResponse('올바른 조회 기간(최대 63일)을 입력하세요.', status=400)
    plans = DietPlan.objects.filter(target_date__range=(start,end), meal_type__in=['조식','중식','석식'])
    plans = sorted(plans, key=lambda p:(p.target_date,['조식','중식','석식'].index(p.meal_type)))
    documents=[]; warnings=[]
    for plan in plans:
        saved = CookingInstruction.objects.filter(diet_plan=plan).first() or CookingInstruction(diet_plan=plan)
        sheet = cooking_sheet(plan, saved.line_notes)
        warnings.extend(sheet['warnings'])
        menus={}
        for row in sheet['rows']:
            total = f"{row.get('total_display', '계산 불가')} {row.get('unit', '')}"
            if row.get('package') is not None:
                total += f" ({row['package_display']} {row['package_unit']} 사용분)"
            menus.setdefault(row['menu'], []).append({'name':row['ingredient'], 'total_qty':total,
                'remark':' / '.join(filter(None,[row.get('notes'),row.get('remark'),row.get('specification')]))})
        menu_rows=[{'name':name,'rowspan':len(rows),'ingredients':rows} for name,rows in menus.items()]
        documents.append({'date_str':str(plan.target_date), 'target_date':str(plan.target_date),
            'meal_type':plan.meal_type, 'headcount':sheet['headcount'] if sheet['confirmed'] else '미확정',
            'rowspan':max(1,len(sheet['rows'])), 'menus':menu_rows,
            'instructions':saved.instructions,'inventory_instructions':saved.inventory_instructions,
            'edit_url':reverse('meals:cooking_detail',args=[plan.pk])})
    pages=[]; chunk=[]; count=0
    for document in documents:
        if chunk and count+document['rowspan']>25:
            pages.append({'page_num':len(pages)+1,'diet_plans':chunk});chunk=[];count=0
        chunk.append(document);count+=document['rowspan']
    if chunk:pages.append({'page_num':len(pages)+1,'diet_plans':chunk})
    return render(request,'docs/doc_cooking_instruction.html', {'start_date':str(start),'end_date':str(end),
        'diet_plans':documents,'pages':pages,'total_pages':len(pages),'warnings':warnings})
