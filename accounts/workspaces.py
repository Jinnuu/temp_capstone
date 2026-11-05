from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from .rbac import can, is_main, roles


def allowed_workspaces(user):
    options = []
    if can(user, 'accounts.manage'):
        options.append(('최고관리자' if is_main(user) else '운영 관리자', 'account_admin_dashboard'))
    if user.role == 'SUPPLIER' and can(user, 'portal.read'):
        options.append(('공급업체 수주·납품', 'procurement:portal_home'))
    if can(user, 'meals.write'):
        options.append(('영양사 업무', 'home'))
    if can(user, 'inventory.write'):
        options.append(('입고·검수·재고', 'procurement:workflow_inspections'))
    if can(user, 'cooking.write'):
        options.append(('조리 업무', 'meals:cooking_index'))
    if not options and can(user, 'dashboard.read'):
        options.append(('조회 업무', 'home'))
    return options


def landing_url(user):
    options = allowed_workspaces(user)
    return reverse(options[0][1]) if options else reverse('home')


@require_GET
def choose_workspace(request):
    return render(request, 'accounts/workspaces.html', {'workspaces': allowed_workspaces(request.user)})
