"""Business records require an authenticated internal operator."""
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


class BusinessAccessMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        public=request.path.startswith(('/accounts/','/static/','/admin/'))
        if not public:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(),settings.LOGIN_URL)
            if getattr(request.user,'role',None)=='SUPPLIER' and not request.user.is_staff:
                return HttpResponseForbidden('업무 데이터는 영양사·관리자만 접근할 수 있습니다.')
        return self.get_response(request)
