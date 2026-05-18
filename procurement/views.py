from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import datetime, date, timedelta

from .models import PurchaseOrder, OrderItem
from inventory.models import Ingredient, InventoryLog
from forecasting.services.ingredient_calc import get_all_day_requirements
from datetime import date
from meals.models import DietPlan, DietMenu
from django.db.models import Case, When, Value, IntegerField

CATEGORY_ORDER = ['밥', '국', '주반찬', '부반찬', '김치', '간식']
SORT_ORDER = Case(
    *[When(menu__category=cat, then=Value(pos)) for pos, cat in enumerate(CATEGORY_ORDER)],
    default=Value(len(CATEGORY_ORDER)),
    output_field=IntegerField(),
)

def get_or_create_dummy_user(request):
    if request.user.is_authenticated:
        return request.user
    User = get_user_model()
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='admin_dummy', password='dummy_password')
    return user

def order_create(request):
    """
    간편주문(발주서 작성) 생성 뷰 - 날짜별 부족분 로드 기능 포함
    """
    if request.method == 'POST':
        ingredient_ids = request.POST.getlist('ingredient_id[]')
        quantities = request.POST.getlist('quantity[]')
        
        if ingredient_ids and quantities:
            user = get_or_create_dummy_user(request)
            po = PurchaseOrder.objects.create(supplier=user, status=PurchaseOrder.Status.PENDING)
            total_amount = 0
            
            for ing_id, qty in zip(ingredient_ids, quantities):
                if not qty or float(qty) <= 0:
                    continue
                    
                ing = get_object_or_404(Ingredient, id=ing_id)
                q = float(qty)
                estimated = int(q * ing.unit_price)
                total_amount += estimated
                
                OrderItem.objects.create(
                    purchase_order=po,
                    ingredient=ing,
                    required_qty=q,
                    missing_qty=q,
                    order_unit_price=ing.unit_price,
                    estimated_price=estimated
                )
                
            po.total_amount = total_amount
            po.save()
            messages.success(request, f"발주서 #{po.id} 건이 성공적으로 전송되었습니다.")
            return redirect('procurement:order_detail', pk=po.id)
            
    # --- GET 요청 처리 ---
    # 1. 외부(예측 페이지)에서 넘어온 데이터 수신
    items_names = request.GET.getlist('items')
    amounts = request.GET.getlist('amounts')
    shortage_map = dict(zip(items_names, amounts))

    # 2. 🔥 날짜 선택에 따른 부족분 로드 로직
    target_date = request.GET.get('target_date')
    
    if target_date:
        # 선택된 날짜의 통합 부족분을 계산해오는 서비스 호출
        requirements = get_all_day_requirements(target_date)
        
        # 산출된 부족분 아이템들을 shortage_map에 병합
        for name, data in requirements['items'].items():
            if data.get('order_amount', 0) > 0:
                # 이미 리스트에 수량이 있다면 덮어쓰지 않고, 없을 때만 추가 (혹은 합산 선택 가능)
                shortage_map[name] = str(data['order_amount'])

    # 디버깅용 로그
    print(f"--- [DEBUG] 최종 shortage_map: {shortage_map} (날짜: {target_date}) ---")

    ingredients = Ingredient.objects.all().order_by('name')
    categories = (
        Ingredient.objects.exclude(category__isnull=True)
        .exclude(category__exact='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    
    return render(request, "procurement/order_create.html", {
        'ingredients': ingredients,
        'categories': categories,
        'shortage_map': shortage_map,
        'target_date': target_date or date.today().isoformat(), # 템플릿 날짜 input용
    })

def order_list(request):
    """
    발주 내역 목록 조회 (영양사용: 모든 업체의 발주 내역을 조회)
    """
    # 모든 발주 내역 조회 (최신순)
    orders = PurchaseOrder.objects.all().order_by('-created_at')
        
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status')
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    if status_filter and status_filter != '전체':
        orders = orders.filter(status=status_filter)

    # 1. 기존 전체 발주 내역을 위한 업체별 그룹화 (오류방지용으로 남겨둠 or 삭제가능)
    from collections import defaultdict
    orders_by_supplier = defaultdict(list)
    for order in orders:
        orders_by_supplier[order.supplier].append(order)
    
    # 2. 새로운 '식단일 기준' 아이템 그룹화
    items = OrderItem.objects.select_related('purchase_order', 'ingredient', 'purchase_order__supplier').order_by('target_date', 'meal_type', 'menu_name', 'ingredient__name')
    if start_date:
        items = items.filter(target_date__gte=start_date)
    if end_date:
        items = items.filter(target_date__lte=end_date)
    if status_filter and status_filter != '전체':
        items = items.filter(purchase_order__status=status_filter)
        
    supplier_items = defaultdict(list)
    for item in items:
        supplier_items[item.purchase_order.supplier].append(item)
    
    supplier_items_groups = []
    for supplier, s_items in supplier_items.items():
        supplier_items_groups.append({
            'supplier': supplier,
            'items': s_items
        })
    supplier_items_groups.sort(key=lambda x: x['supplier'].name or x['supplier'].username)

    return render(request, "procurement/order_list.html", {
        'orders': orders,
        'supplier_items_groups': supplier_items_groups,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status_filter
    })

def order_detail(request, pk):
    """
    특정 발주서 상세 내역 확인
    """
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    # 끼니 정렬 순서 정의
    MEAL_ORDER = Case(
        When(meal_type='조식', then=Value(1)),
        When(meal_type='중식', then=Value(2)),
        When(meal_type='석식', then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    # 연관된 품목들 (날짜 및 끼니순 정렬)
    items = order.items.select_related('ingredient').order_by('target_date', MEAL_ORDER, 'menu_name', 'ingredient__name')
    
    subtotal = order.total_amount
    vat = int(subtotal * 0.1)
    total = subtotal + vat
    
    return render(request, "procurement/order_detail.html", {
        'order': order,
        'items': items,
        'subtotal': subtotal,
        'vat': vat,
        'total': total
    })

def order_status_update(request, pk):
    """
    발주 상태 변경 및 배송 완료 시 자동 입고 처리
    """
    if request.method == 'POST':
        order = get_object_or_404(PurchaseOrder, pk=pk)
        new_status = request.POST.get('status')
        
        if new_status in [choice[0] for choice in PurchaseOrder.Status.choices]:
            # 배송 완료(DELIVERED)로 변경될 때만 재고에 반영
            if new_status == PurchaseOrder.Status.DELIVERED and order.status != PurchaseOrder.Status.DELIVERED:
                for item in order.items.all():
                    ing = item.ingredient
                    # 재석님이 앞서 사용한 '입고' 로그 생성 로직 적용
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type='입고',  # 한글 기반 문자열 매칭
                        quantity=item.required_qty,
                        description=f"발주 #{order.id} 배송 완료로 인한 자동 입고"
                    )
            
            order.status = new_status
            order.save()
            messages.success(request, f"발주서 #{order.id}의 상태가 변경되었습니다.")
            
    return redirect('procurement:order_detail', pk=pk)

def order_from_mealplan(request):
    """
    식단 데이터(DietPlan)를 분석하여 식재료 필요량을 계산하고,
    메뉴별 상세 조정 기능을 제공하는 스마트 발주 생성 뷰
    """
    if request.method == 'POST':
        # 1. 업체(Supplier)별 및 날짜별로 그룹화 (발주처별/날짜별로 별개의 발주서 생성을 위함)
        ingredient_ids = request.POST.getlist('ingredient_id[]')
        quantities = request.POST.getlist('quantity[]')
        target_dates = request.POST.getlist('target_date[]')
        meal_types = request.POST.getlist('meal_type[]')
        menu_names = request.POST.getlist('menu_name[]')
        
        # 구조: order_data[(sup_id, target_date)] = { (ing_id, meal_type, menu_name): total_qty }
        order_data = {} 
        
        for ing_id_str, qty_str, dt_str, mt_str, mn_str in zip(ingredient_ids, quantities, target_dates, meal_types, menu_names):
            try:
                ing_id = int(ing_id_str)
                q = float(qty_str or 0)
            except (ValueError, TypeError):
                continue
                
            if q <= 0: continue
            
            ing = get_object_or_404(Ingredient, id=ing_id)
            if not ing.supplier:
                continue
                
            sup_id = ing.supplier.id
            dt = dt_str if dt_str else None
            
            # 발주처와 날짜의 조합을 최상위 키로 사용
            po_key = (sup_id, dt)
            if po_key not in order_data:
                order_data[po_key] = {}
            
            # 내부는 식재료, 끼니, 메뉴명으로 구분
            item_key = (ing_id, mt_str if mt_str else None, mn_str if mn_str else None)
            if item_key not in order_data[po_key]:
                order_data[po_key][item_key] = 0
            order_data[po_key][item_key] += q
            
        if not order_data:
            messages.error(request, "발주할 품목이 없습니다.")
            return redirect('procurement:order_from_mealplan')

        # 2. 트랜잭션 내에서 각 (업체+날짜)별 발주서 생성
        with transaction.atomic():
            created_po_ids = []
            for (sup_id, target_date), items_dict in order_data.items():
                supplier_user = get_user_model().objects.get(id=sup_id)
                po = PurchaseOrder.objects.create(
                    supplier=supplier_user,
                    status=PurchaseOrder.Status.PENDING,
                    total_amount=0
                )
                
                po_total = 0
                for (ing_id, mt_str, mn_str), q in items_dict.items():
                    ing = Ingredient.objects.get(id=ing_id)
                    subtotal = int(q * ing.unit_price)
                    po_total += subtotal
                    OrderItem.objects.create(
                        purchase_order=po,
                        ingredient=ing,
                        target_date=dt_str if dt_str else None,
                        meal_type=mt_str,
                        menu_name=mn_str,
                        required_qty=q,
                        missing_qty=q,
                        order_unit_price=ing.unit_price,
                        estimated_price=subtotal
                    )
                
                po.total_amount = po_total
                po.save()
                created_po_ids.append(po.id)
                
            messages.success(request, f"총 {len(created_po_ids)}건의 업체별 발주서가 성공적으로 생성되었습니다.")
            return redirect('procurement:order_list')

    # --- GET: 식단 기반 데이터 분석 ---
    # 기본값: 오늘부터 7일치
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = date.today()
    else:
        start_date = date.today()
        
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = start_date + timedelta(days=6)
    else:
        end_date = start_date + timedelta(days=6)

    # 끼니 정렬 순서 정의
    MEAL_ORDER = Case(
        When(meal_type='조식', then=Value(1)),
        When(meal_type='중식', then=Value(2)),
        When(meal_type='석식', then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    # 해당 기간의 식단 조회 (식재료 및 공급업체 정보까지 미리 로드)
    plans = DietPlan.objects.filter(
        target_date__gte=start_date,
        target_date__lte=end_date
    ).prefetch_related('diet_menus__menu__recipes__ingredient__supplier').order_by('target_date', MEAL_ORDER)

    # 데이터 구조화 (날짜별로 먼저 그룹화)
    analysis_data = {} # date -> list of plans
    for plan in plans:
        dt = plan.target_date
        if dt not in analysis_data:
            analysis_data[dt] = []
        
        plan_item = {
            'meal_type': plan.meal_type,
            'headcount': plan.headcount,
            'menus': [],
            'total_ingredients': 0
        }
        
        # 메뉴 정렬 순서 적용 (밥-국-주-부-김-간)
        sorted_diet_menus = plan.diet_menus.all().select_related('menu').order_by(SORT_ORDER)
        
        for dm in sorted_diet_menus:
            menu = dm.menu
            menu_item = {'id': menu.id, 'name': menu.name, 'ingredients': []}
            for recipe in menu.recipes.all():
                ing = recipe.ingredient
                needed_qty = float(plan.headcount) * float(recipe.required_amount)
                menu_item['ingredients'].append({
                    'id': ing.id, 'name': ing.name, 'unit': ing.unit,
                    'price': ing.unit_price, 'category': ing.category,
                    'spec': ing.spec, 'description': ing.description,
                    'supplier_name': ing.supplier.name if ing.supplier else "미정",
                    'needed_qty': round(needed_qty, 2),
                })
                plan_item['total_ingredients'] += 1
            if not menu_item['ingredients']:
                # If a menu has no ingredients, it still takes 1 row to show the menu name, 
                # so we need to account for it in the rowspan if we decide to render it,
                # but currently the template loops over menu.ingredients. 
                # Wait, if there are no ingredients, the menu row won't render at all because of `for ing in menu.ingredients`.
                pass
            plan_item['menus'].append(menu_item)
            
        if plan_item['total_ingredients'] == 0:
            plan_item['total_ingredients'] = 1 # To prevent rowspan="0" or empty
            
        analysis_data[dt].append(plan_item)

    # 템플릿에서 순서대로 출력하기 위해 리스트로 정렬
    sorted_analysis = []
    for dt in sorted(analysis_data.keys()):
        sorted_analysis.append({
            'date': dt,
            'plans': analysis_data[dt]
        })

    all_ingredients = Ingredient.objects.all().order_by('name')

    context = {
        'start_date': start_date, 'end_date': end_date,
        'analysis_data': sorted_analysis, 'all_ingredients': all_ingredients,
    }
    return render(request, "procurement/order_from_mealplan.html", context)