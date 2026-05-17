from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import PurchaseOrder, OrderItem
from inventory.models import Ingredient, InventoryLog
from forecasting.services.ingredient_calc import get_all_day_requirements
from datetime import date

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
    발주 내역 목록 조회
    """
    user = get_or_create_dummy_user(request)
    orders = PurchaseOrder.objects.filter(supplier=user).order_by('-created_at')
    
    if not orders.exists():
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
        
    return render(request, "procurement/order_list.html", {
        'orders': orders,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status_filter
    })

def order_detail(request, pk):
    """
    특정 발주서 상세 내역 확인
    """
    order = get_object_or_404(PurchaseOrder, pk=pk)
    items = order.items.all()
    
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