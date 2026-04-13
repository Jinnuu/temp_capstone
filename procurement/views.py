from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import PurchaseOrder, OrderItem
from inventory.models import Ingredient, InventoryLog

def get_or_create_dummy_user(request):
    if request.user.is_authenticated:
        return request.user
    User = get_user_model()
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='admin_dummy', password='dummy_password')
    return user

def order_create(request):
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
            
    ingredients = Ingredient.objects.all().order_by('name')
    # Filter out empty or None categories
    categories = Ingredient.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category', flat=True).distinct()
    
    return render(request, "procurement/order_create.html", {
        'ingredients': ingredients,
        'categories': categories,
    })

def order_list(request):
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
    if request.method == 'POST':
        order = get_object_or_404(PurchaseOrder, pk=pk)
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in PurchaseOrder.Status.choices]:
            if new_status == '완료' and order.status != '완료':
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

