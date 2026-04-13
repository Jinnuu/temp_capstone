from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import PurchaseOrder, OrderItem
from inventory.models import Ingredient, InventoryLog

def get_or_create_dummy_user(request):
    """
    인증된 사용자가 없을 경우 테스트를 위한 더미 사용자를 반환합니다.
    """
    if request.user.is_authenticated:
        return request.user
    User = get_user_model()
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='admin_dummy', password='dummy_password')
    return user

def order_create(request):
    """
    간편주문(발주서 작성) 생성 뷰
    GET: 선택된 품목(selected_ids)을 받아와서 자동 체크된 상태로 페이지 노출
    POST: 선택된 품목들과 수량을 바탕으로 PurchaseOrder 및 OrderItem 생성
    """
    if request.method == 'POST':
        ingredient_ids = request.POST.getlist('ingredient_id[]')
        quantities = request.POST.getlist('quantity[]')
        
        if ingredient_ids and quantities:
            user = get_or_create_dummy_user(request)
            # 발주서 기본 객체 생성 (상태: 대기중)
            po = PurchaseOrder.objects.create(supplier=user, status=PurchaseOrder.Status.PENDING)
            total_amount = 0
            
            # 전송된 데이터 매칭 (zip 사용)
            for ing_id, qty in zip(ingredient_ids, quantities):
                # 수량이 없거나 0 이하인 경우는 제외
                if not qty or float(qty) <= 0:
                    continue
                    
                ing = get_object_or_404(Ingredient, id=ing_id)
                q = float(qty)
                estimated = int(q * ing.unit_price)
                total_amount += estimated
                
                # 상세 품목(OrderItem) 저장
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
<<<<<<< HEAD
            return redirect('procurement:order_detail', pk=po.id) # URL 네임스페이스 확인 필요
=======
            return redirect('procurement:order_detail', pk=po.id)
>>>>>>> origin/feat/procurement-system-upgrades
            
    # --- GET 요청 처리 ---
    
    # 1. URL 파라미터에서 선택된 ID들 가져오기 (예: ?selected_ids=1,2,5)
    selected_ids_raw = request.GET.get('selected_ids', '')
    # 콤마로 구분된 문자열을 리스트로 변환 (빈 문자열인 경우 빈 리스트)
    selected_ids = selected_ids_raw.split(',') if selected_ids_raw else []

    # 2. 전체 식재료 목록 (이름순 정렬)
    ingredients = Ingredient.objects.all().order_by('name')
    
    # 3. 카테고리 필터용 목록 (비어있지 않은 대분류만 추출)
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
        'selected_ids': selected_ids, # 🔥 템플릿에서 {% if ing.id|stringformat:"s" in selected_ids %} 로 사용
    })

def order_list(request):
    """
    발주 내역 목록 조회 (필터링 포함)
    """
    user = get_or_create_dummy_user(request)
    orders = PurchaseOrder.objects.filter(supplier=user).order_by('-created_at')
    
    # 내역이 아예 없는 경우 전체 노출 (테스트용)
    if not orders.exists():
        orders = PurchaseOrder.objects.all().order_by('-created_at')
        
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status')
    
    # 필터 적용
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
    items = order.items.all() # OrderItem 역참조
    
    subtotal = order.total_amount
    vat = int(subtotal * 0.1)
    total = subtotal + vat
    
    return render(request, "procurement/order_detail.html", {
        'order': order,
        'items': items,
        'subtotal': subtotal,
        'vat': vat,
        'total': total
<<<<<<< HEAD
    })
=======
    })

def order_status_update(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(PurchaseOrder, pk=pk)
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in PurchaseOrder.Status.choices]:
            if new_status == PurchaseOrder.Status.DELIVERED and order.status != PurchaseOrder.Status.DELIVERED:
                # 입고 처리 로직
                for item in order.items.all():
                    ing = item.ingredient
                    ing.current_stock += item.required_qty
                    ing.save()
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type=InventoryLog.LogType.IN,
                        quantity=item.required_qty,
                        description=f"발주 #{order.id} 입고"
                    )
            order.status = new_status
            order.save()
            messages.success(request, f"발주서 #{order.id}의 상태가 '{new_status}'(으)로 변경되었습니다.")
    return redirect('procurement:order_detail', pk=pk)

def order_delete(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(PurchaseOrder, pk=pk)
        order.delete()
        messages.success(request, f"해당 발주서 내역이 완전히 삭제되었습니다.")
    return redirect('procurement:order_list')
>>>>>>> origin/feat/procurement-system-upgrades
