"""Server-side authorization, independent of navigation and HTTP clients."""
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from accounts.rbac import can, account_can_login, required_capability

PUBLIC_NAMES = {
    'login', 'logout', 'signup', 'username_recovery', 'password_reset',
    'recovery_requested', 'username_recovery_confirm', 'username_confirm',
    'password_reset_complete', 'password_reset_confirm',
}


class BusinessAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        name = request.resolver_match.view_name
        public = name in PUBLIC_NAMES or request.path.startswith('/static/')
        if request.user.is_authenticated and not account_can_login(request.user):
            logout(request)
        if public:
            return None
        if not request.user.is_authenticated:
            if name == 'admin:login':
                return None
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if name=='home' and can(request.user,'portal.read') and not can(request.user,'dashboard.read'):
            return redirect('procurement:portal_home')
        cap = required_capability(name, request.method)
        if not cap or not can(request.user, cap):
            if cap in ('accounts.manage','admins.manage'):
                from accounts.access_service import audit
                audit(request.user, None, 'admin.access_denied', result='DENIED', reason='insufficient_permission')
            return HttpResponseForbidden('이 작업을 수행할 권한이 없습니다. 관리자에게 역할을 확인해 주세요.')
        request.snp_required_capability = cap
        return None
