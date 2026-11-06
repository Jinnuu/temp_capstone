"""Shared read-only round history; supplier scheduling and buyer inspection separated."""
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from accounts.rbac import can
from .models import PurchaseOrder
from .portal_views import own_orders
from .deliveries import schedule, inspect, progress


def context(order, supplier):
    items = list(order.items.select_related('ingredient'))
    for item in items:
        item.delivery_progress = progress(item)
    return {'order': order, 'items': items, 'supplier_view': supplier,
            'batches': order.delivery_batches.prefetch_related('lines__order_item__ingredient', 'lines__receipt').all(),
            'request_key': uuid.uuid4(), 'today': timezone.localdate()}


@login_required
@require_http_methods(['GET', 'POST'])
def supplier_order(request, pk):
    order = get_object_or_404(own_orders(request), pk=pk)
    status = 200
    if request.method == 'POST':
        try:
            items = list(order.items.all())
            allowed = {'csrfmiddlewaretoken', 'request_key', 'expected_date', 'contact', 'notes'} | {'q_'+str(i.pk) for i in items}
            if set(request.POST)-allowed:
                raise ValidationError('허용되지 않은 납품 설정입니다.')
            values = {str(i.pk): request.POST['q_'+str(i.pk)] for i in items if request.POST.get('q_'+str(i.pk), '').strip()}
            schedule(request.user, order.pk, request_key=request.POST.get('request_key'),
                     expected_date=request.POST.get('expected_date'), quantities=values,
                     contact=request.POST.get('contact', ''), notes=request.POST.get('notes', ''))
            messages.success(request, '납품 회차를 등록했습니다. 구매자 검수 합격 전에는 입고되지 않습니다.')
            return redirect('procurement:portal_deliveries', pk=pk)
        except (ValidationError, ValueError, TypeError) as exc:
            messages.error(request, ' / '.join(exc.messages) if isinstance(exc, ValidationError) else '입력값을 확인하세요.')
            status = 400
    return render(request, 'workflow/deliveries.html', context(order, True), status=status)


@login_required
@require_http_methods(['GET', 'POST'])
def buyer_order(request, pk):
    if not can(request.user, 'inspection.read'):
        raise PermissionDenied
    order = get_object_or_404(PurchaseOrder.objects.select_related('supplier'), pk=pk)
    status = 200
    if request.method == 'POST':
        if not can(request.user, 'inspection.write'):
            raise PermissionDenied
        try:
            allowed = {'csrfmiddlewaretoken', 'line', 'delivered', 'accepted', 'actual_date', 'specification', 'notes', 'expiration'}
            if set(request.POST)-allowed:
                raise ValidationError('허용되지 않은 검수 설정입니다.')
            from .models import DeliveryBatchLine
            line = get_object_or_404(DeliveryBatchLine, batch__order=order, pk=request.POST.get('line'))
            inspect(request.user, line.pk, delivered=request.POST.get('delivered'), accepted=request.POST.get('accepted'),
                    actual_date=request.POST.get('actual_date'), specification=request.POST.get('specification', ''),
                    notes=request.POST.get('notes', ''), expiration=request.POST.get('expiration'))
            messages.success(request, '회차별 검수를 저장하고 합격량만 입고 반영했습니다.')
            return redirect('procurement:delivery_order', pk=pk)
        except (ValidationError, ValueError, TypeError) as exc:
            messages.error(request, ' / '.join(exc.messages) if isinstance(exc, ValidationError) else '입력값을 확인하세요.')
            status = 400
    return render(request, 'workflow/deliveries.html', {**context(order, False), 'can_inspect': can(request.user, 'inspection.write')}, status=status)
