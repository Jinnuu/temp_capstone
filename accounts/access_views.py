import json
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .models import User, AccessAudit
from .rbac import ROLE_LABELS, ROLE_CAPS, roles, approval_mode, capabilities
from .access_service import change_access, AccessRejected, snapshot


@require_GET
def users(request):
    query = request.GET.get('q', '').strip()[:150]
    records = User.objects.prefetch_related('groups').filter(Q(username__icontains=query)|Q(name__icontains=query)|Q(email__icontains=query)).order_by('username')
    state = request.GET.get('state', '')
    if state in User.AccountState.values:
        records = records.filter(account_state=state)
    records = list(records[:200])
    for item in records:
        item.app_role_summary = ', '.join(ROLE_LABELS[name] for name in sorted(roles(item))) or '내부 역할 없음'
    return render(request, 'accounts/manage_users.html', {'records': records, 'query': query, 'states': User.AccountState.choices, 'selected_state': state, 'approval_mode': approval_mode()})


@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    target = get_object_or_404(User, pk=pk)
    status = 200
    if request.method == 'POST':
        try:
            revision = int(request.POST.get('revision', ''))
            target, changed = change_access(request.user, pk, state=request.POST.get('state'), new_roles=request.POST.getlist('roles'), revision=revision)
            messages.success(request, '계정 설정을 저장했습니다.' if changed else '변경 사항이 없습니다.')
            return redirect('account_admin_detail', pk=pk)
        except (ValueError, AccessRejected) as exc:
            messages.error(request, '입력값이 올바르지 않습니다.' if isinstance(exc, ValueError) else ' '.join(exc.messages))
            status = 409 if getattr(exc, 'code', '') == 'conflict' else 400
            target.refresh_from_db()
    return render(request, 'accounts/manage_detail.html', {'target': target, 'roles': ROLE_LABELS.items(), 'selected_roles': roles(target), 'effective_caps': sorted(capabilities(target)), 'states': User.AccountState.choices, 'history': AccessAudit.objects.filter(target=target)[:30]}, status=status)


@require_http_methods(['GET', 'POST'])
def api(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == 'GET':
        return JsonResponse({**snapshot(target), 'capabilities': sorted(capabilities(target))})
    try:
        body = json.loads(request.body)
        if not isinstance(body, dict) or set(body) - {'state', 'roles', 'revision'}:
            raise ValueError()
        if type(body.get('revision')) is not int or ('roles' in body and (not isinstance(body['roles'], list) or not all(isinstance(x, str) for x in body['roles']))):
            raise ValueError()
        target, changed = change_access(request.user, pk, state=body.get('state'), new_roles=body.get('roles'), revision=body['revision'])
        return JsonResponse({'changed': changed, **snapshot(target)})
    except (ValueError, TypeError):
        return JsonResponse({'error': '입력값이 올바르지 않습니다.'}, status=400)
    except AccessRejected as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=409 if exc.code == 'conflict' else 400)


@require_GET
def matrix(request):
    caps = sorted(set().union(*ROLE_CAPS.values()))
    rows = [(cap, [(role, cap in ROLE_CAPS[role]) for role in ROLE_LABELS]) for cap in caps]
    return render(request, 'accounts/manage_matrix.html', {'role_headers': ROLE_LABELS.values(), 'rows': rows, 'approval_mode': approval_mode()})


@require_GET
def logs(request):
    records = AccessAudit.objects.all()
    if request.GET.get('result') in ('SUCCESS', 'DENIED'):
        records = records.filter(result=request.GET['result'])
    return render(request, 'accounts/manage_audit.html', {'records': records[:200]})
