from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from accounts.access_service import AccessRejected
from .models import SupplierMembership, Supplier, PurchaseOrder, SupplierFulfillment
from .portal_services import verified_membership, update_fulfillment, review_membership, TRANSITIONS


def own_orders(request):
    member=verified_membership(request.user)
    return PurchaseOrder.objects.filter(supplier_id=member.supplier.user_id).select_related('supplier','fulfillment').prefetch_related('items__ingredient','items__delivery_plan','items__inspection')


@require_GET
def portal_home(request):
    member=SupplierMembership.objects.select_related('supplier').filter(account=request.user).first()
    if not member or member.status!='VERIFIED':
        return render(request,'portal/pending.html',{'membership':member})
    orders=own_orders(request)
    counts={'new':orders.filter(fulfillment__isnull=True).exclude(status__in=['완료','배송완료']).count()+orders.filter(fulfillment__state='NEW').exclude(status__in=['완료','배송완료']).count(),
        'awaiting':orders.filter(Q(fulfillment__isnull=True)|Q(fulfillment__state__in=['NEW','ACKNOWLEDGED'])).exclude(status__in=['완료','배송완료']).count(),
        'scheduled':orders.filter(fulfillment__state='ACCEPTED').exclude(status__in=['완료','배송완료']).count(),
        'preparing':orders.filter(fulfillment__state='PREPARING').exclude(status__in=['완료','배송완료']).count(),
        'completed':orders.filter(status__in=['완료','배송완료']).count(),
        'rejected':orders.filter(fulfillment__state='REJECTED').count()}
    return render(request,'portal/home.html',{'membership':member,'counts':counts,'orders':orders.order_by('-created_at')[:10], 'deliveries':orders.filter(fulfillment__delivery_date__gte=timezone.localdate()).exclude(status__in=['완료','배송완료']).order_by('fulfillment__delivery_date')[:15]})


@require_GET
def portal_orders(request):
    orders=own_orders(request)
    q=request.GET.get('q','').strip()[:100]
    if q:
        filt=Q(items__ingredient__name__icontains=q)
        if q.isdecimal():filt|=Q(pk=int(q))
        orders=orders.filter(filt).distinct()
    state=request.GET.get('state','')
    if state=='NEW':orders=orders.filter(Q(fulfillment__isnull=True)|Q(fulfillment__state='NEW')).exclude(status__in=['완료','배송완료'])
    elif state in TRANSITIONS:orders=orders.filter(fulfillment__state=state)
    sort={'oldest':'created_at','newest':'-created_at','delivery':'fulfillment__delivery_date'}.get(request.GET.get('sort'),' -created_at'.strip())
    orders=orders.order_by(sort,'pk')[:200]
    if request.GET.get('format')=='json':
        return JsonResponse({'orders':[{'id':o.pk,'status':o.status,'amount':o.total_amount,'fulfillment':getattr(getattr(o,'fulfillment',None),'state',None if o.status in ('완료','배송완료') else 'NEW')} for o in orders]})
    return render(request,'portal/orders.html',{'orders':orders,'query':q,'states':SupplierFulfillment._meta.get_field('state').choices})


@require_http_methods(['GET','POST'])
def portal_detail(request,pk):
    order=get_object_or_404(own_orders(request),pk=pk)
    status=200
    if request.method=='POST':
        try:
            items=list(order.items.all())
            allowed={'csrfmiddlewaretoken','state','revision','delivery_date','rejection_reason','notes'}|{'q_'+str(i.pk) for i in items}
            if set(request.POST)-allowed:raise AccessRejected('허용되지 않은 발주 설정입니다.')
            quantities={str(i.pk):request.POST['q_'+str(i.pk)] for i in items if 'q_'+str(i.pk) in request.POST and request.POST['q_'+str(i.pk)].strip()}
            update_fulfillment(request.user,pk,state=request.POST.get('state',''),revision=int(request.POST.get('revision','')),delivery_date=request.POST.get('delivery_date'),quantities=quantities,rejection_reason=request.POST.get('rejection_reason',''),notes=request.POST.get('notes',''))
            messages.success(request,'수주·납품 정보를 저장했습니다. 검수 전에는 재고가 증가하지 않습니다.')
            return redirect('procurement:portal_detail',pk=pk)
        except (AccessRejected,ValueError) as exc:
            messages.error(request,'입력값을 확인하세요.' if isinstance(exc,ValueError) else ' '.join(exc.messages))
            status=409 if getattr(exc,'code','')=='conflict' else 400
            order=get_object_or_404(own_orders(request),pk=pk)
    from .deliveries import progress
    for item in order.items.all():
        item.delivery_progress=progress(item)
    current=getattr(order,'fulfillment',None)
    state=current.state if current else 'NEW'
    allowed_states=sorted(TRANSITIONS[state]|({state} if state not in ('DISPATCHED','REJECTED') else set()))
    if order.status not in ('대기','승인') or order.needs_review or order.delivery_batches.exists() or order.items.filter(inspection__isnull=False).exists():allowed_states=[]
    if request.GET.get('format')=='json' and request.method=='GET':
        return JsonResponse({'id':order.pk,'state':None if current is None and order.status in ('완료','배송완료') else state,'buyer_status':order.status,'revision':current.revision if current else 0,'items':[{'id':i.pk,'name':i.ingredient.name,'quantity':str(i.purchase_quantity),'unit':i.purchase_unit,'base_quantity':str(i.required_qty),'base_unit':i.ingredient.unit} for i in order.items.all()]})
    return render(request,'portal/detail.html',{'order':order,'fulfillment':current,'allowed_states':[(value,label) for value,label in SupplierFulfillment._meta.get_field('state').choices if value in allowed_states],'today':timezone.localdate()},status=status)


@require_GET
def portal_export(request,pk):
    order=get_object_or_404(own_orders(request),pk=pk)
    from .views import export_vendor_procurement_excel
    dates=[item.target_date or order.created_at.date() for item in order.items.all()]
    if not dates:return HttpResponseBadRequest('품목이 없습니다.')
    if (max(dates)-min(dates)).days>366:return HttpResponseBadRequest('출력 기간을 확인하세요.')
    query=request.GET.copy()
    query['supplier_id']=str(order.supplier_id)
    query['start_date']=str(min(dates)-timedelta(days=4));query['end_date']=str(max(dates))
    request.GET=query
    request.snp_portal_order=order
    return export_vendor_procurement_excel(request)


@require_http_methods(['GET','POST'])
def membership_reviews(request):
    status=200
    if request.method=='POST':
        try:
            allowed={'csrfmiddlewaretoken','membership','supplier','revision','create_company','reject','note'}
            if set(request.POST)-allowed:raise ValueError()
            member_id=int(request.POST.get('membership',''))
            get_object_or_404(SupplierMembership,pk=member_id)
            review_membership(request.user,member_id,request.POST.get('supplier') or None,int(request.POST.get('revision','')),create_company=request.POST.get('create_company')=='1',reject=request.POST.get('reject')=='1',note=request.POST.get('note',''))
            messages.success(request,'업체 소속 확인을 저장했습니다.')
            return redirect('procurement:membership_reviews')
        except (ValueError,AccessRejected) as exc:
            messages.error(request,'입력값을 확인하세요.' if isinstance(exc,ValueError) else ' '.join(exc.messages));status=400
    from accounts.rbac import is_main, is_admin_identity
    members=list(SupplierMembership.objects.select_related('account','supplier').prefetch_related('account__groups').order_by('status','pk')[:200])
    if not is_main(request.user):members=[item for item in members if not is_admin_identity(item.account)]
    return render(request,'portal/membership_reviews.html',{'memberships':members,'suppliers':Supplier.objects.select_related('user').filter(user__role='SUPPLIER').order_by('name')},status=status)
