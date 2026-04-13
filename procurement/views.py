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
    selected_ids_raw = request.GET.get('selected_ids', '')
    selected_ids = selected_ids_raw.split(',') if selected_ids_raw else []

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
        'selected_ids': selected_ids,
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

def order_delete(request, pk):
    """
    발주 내역 삭제
    """
    if request.method == 'POST':
        order = get_object_or_404(PurchaseOrder, pk=pk)
        order.delete()
        messages.success(request, f"발주서 #{pk} 내역이 삭제되었습니다.")
    return redirect('procurement:order_list')