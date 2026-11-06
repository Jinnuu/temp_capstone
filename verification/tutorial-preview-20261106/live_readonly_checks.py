"""Run inside deployed Preview. SELECT/render only; never authenticate or save."""
import json,hashlib
from pathlib import Path
import django
django.setup()
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve
from django.contrib.messages.storage.fallback import FallbackStorage
from accounts.models import User
from accounts.rbac import is_main,can,public_signup_requires_approval
assert settings.DATABASES['default']['NAME']=='snp_ui_preview' and settings.DATABASES['default']['HOST']=='db'
users=User.objects.only('pk','username','name','role','rbac_managed','account_state','is_active','is_staff','is_superuser').prefetch_related('groups')
main=users.get(pk=1)
assert main.username=='admin' and is_main(main) and main.is_active and main.is_superuser and main.is_staff
assert not User.objects.filter(username='verify-admin').exists()
assert User.objects.filter(username='admin').count()==1
assert public_signup_requires_approval()

def render(path,user):
    request=RequestFactory().get(path,secure=True,HTTP_HOST='ui.jinnuu.site')
    request.user=user;request.session={};request._messages=FallbackStorage(request)
    match=resolve(path);request.resolver_match=match
    response=match.func(request,**match.kwargs)
    if hasattr(response,'render'):response.render()
    assert response.status_code==200
    return response.content.decode()

guide=render('/procurement/workflow/',main)
assert '영양사 업무 가이드' in guide and guide.count('data-guide-step=')==6 and 'name="manual"' not in guide
headcounts=render('/procurement/workflow/headcounts/',main)
assert 'name="manual"' in headcounts and '식수 저장' in headcounts
plans=render('/procurement/workflow/plans/',main);assert '저장한 발주예정서' in plans
signup=render('/accounts/signup/',AnonymousUser())
assert '회원가입 후 바로 로그인' not in signup and '계정 승인 후 로그인' in signup
files=['accounts/access_service.py','accounts/preview_bootstrap.py','accounts/rbac.py','procurement/supplier_views.py','procurement/workflow_views.py','procurement/tutorial.py','procurement/money.py','forecasting/services/reporting.py','meals/change_policy.py','templates/workflow/tutorial.html','templates/workflow/headcounts.html','templates/accounts/signup.html','static/ui/build/snp-ui.js','static/ui/build/snp-ui.css']
source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files}
print(json.dumps({'passed':True,'main':{'pk':main.pk,'username':main.username,'active':main.is_active,'staff':main.is_staff,'superuser':main.is_superuser,'state':main.account_state},'accounts':User.objects.count(),'main_count':sum(is_main(u) for u in users),'verify_admin_count':0,'public_signup_pending_required':public_signup_requires_approval(),'guide_headcount_and_plan_entries_rendered_readonly':True,'signup_copy_matches_policy':True,'mail_mode':settings.ACCOUNT_RECOVERY_DELIVERY_MODE,'source_hashes':source_hashes,'real_account_login_attempted':False,'business_mutations_attempted':False},indent=2))
