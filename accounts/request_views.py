from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_GET
from .models import AdminRoleRequest
from .admin_requests import submit_request, review_request
from .access_service import AccessRejected


@require_http_methods(['GET','POST'])
def request_admin(request):
    status = 200
    if request.method == 'POST':
        try:
            # Never bind a User or accept role/privilege fields from this form.
            if set(request.POST) - {'csrfmiddlewaretoken','reason'}:
                raise AccessRejected('신청 사유 외의 계정 설정은 제출할 수 없습니다.')
            submit_request(request.user, request.POST.get('reason',''))
            messages.success(request,'관리자 권한 신청을 접수했습니다. 현재 로그인 권한은 유지됩니다.')
            return redirect('admin_request')
        except AccessRejected as exc:
            messages.error(request,' '.join(exc.messages));status=400
    return render(request,'accounts/admin_request.html',{'application':AdminRoleRequest.objects.filter(user=request.user).first()},status=status)


@require_GET
def requests(request):
    return render(request,'accounts/admin_requests.html',{'applications':AdminRoleRequest.objects.select_related('user').order_by('-requested_at')[:200]})


@require_http_methods(['POST'])
def review(request, pk):
    get_object_or_404(AdminRoleRequest, pk=pk)
    try:
        if set(request.POST) - {'csrfmiddlewaretoken','decision','revision','note'}:
            raise ValueError()
        review_request(request.user,pk,request.POST.get('decision'),int(request.POST.get('revision','')),request.POST.get('note',''))
        messages.success(request,'심사 결과를 저장했습니다.')
        return redirect('account_admin_requests')
    except (AccessRejected,ValueError) as exc:
        messages.error(request, '입력값을 확인하세요.' if isinstance(exc,ValueError) else ' '.join(exc.messages))
        return render(request,'accounts/admin_requests.html',{'applications':AdminRoleRequest.objects.select_related('user').order_by('-requested_at')[:200]}, status=409 if getattr(exc,'code','')=='conflict' else 400)


@require_GET
def dashboard(request):
    from .models import User
    from .rbac import is_main, is_admin_identity
    from .access_views import scoped_logs
    from procurement.models import SupplierMembership
    records=list(User.objects.prefetch_related('groups').all())
    if not is_main(request.user):records=[user for user in records if not is_admin_identity(user)]
    return render(request,'accounts/admin_dashboard.html',{'main_admin':is_main(request.user),'user_count':len(records),'pending_count':sum(user.account_state=='PENDING' for user in records),'membership_count':SupplierMembership.objects.filter(status='PENDING').count(),'admin_request_count':AdminRoleRequest.objects.filter(status='PENDING').count() if is_main(request.user) else None,'recent':scoped_logs(request.user)[:8]})
