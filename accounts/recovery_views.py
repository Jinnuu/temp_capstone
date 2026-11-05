import logging
from django.conf import settings
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from .auth_forms import RecoveryEmailForm
from . import recovery

logger=logging.getLogger('accounts.recovery')


@method_decorator(never_cache, name='dispatch')
@method_decorator(sensitive_post_parameters('email','new_password1','new_password2'), name='dispatch')
class RecoveryPrivacyMixin:
    def dispatch(self, request, *args, **kwargs):
        response=super().dispatch(request,*args,**kwargs)
        response['Referrer-Policy']='same-origin'
        if getattr(self,'token_entry',False) or (kwargs.get('token') and kwargs['token'] != 'set-password'):
            response['Referrer-Policy']='no-referrer'
        return response

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context.update(delivery_available=recovery.delivery_available(), test_delivery=getattr(settings,'ACCOUNT_RECOVERY_DELIVERY_MODE','disabled')=='test')
        return context


class RecoveryRequestMixin:
    template_name='accounts/recovery_request.html'
    success_url=reverse_lazy('recovery_requested')

    def form_valid(self, form):
        if not recovery.delivery_available():
            form.add_error(None,recovery.UNAVAILABLE)
            return self.render_to_response(self.get_context_data(form=form),status=503)
        try:
            allowed=recovery.enqueue(self.recovery_kind,form.cleaned_data['email'].strip().lower(),self.request.META.get('REMOTE_ADDR','unknown'))
        except Exception:
            logger.error('Recovery queue unavailable.')
            form.add_error(None,recovery.UNAVAILABLE)
            return self.render_to_response(self.get_context_data(form=form),status=503)
        if not allowed:
            form.add_error(None,'요청이 많습니다. 잠시 후 다시 시도해 주세요.')
            response=self.render_to_response(self.get_context_data(form=form),status=429)
            response['Retry-After']='3600'
            return response
        return redirect(self.success_url)


from django.views.generic.edit import FormView
class UsernameRequestView(RecoveryPrivacyMixin,RecoveryRequestMixin,FormView):
    form_class=RecoveryEmailForm
    recovery_kind='username'
    extra_context={'recovery_title':'아이디 찾기'}


class PasswordRequestView(RecoveryPrivacyMixin,RecoveryRequestMixin,PasswordResetView):
    recovery_kind='password'
    template_name='accounts/recovery_request.html'
    extra_context={'recovery_title':'비밀번호 재설정'}


class RecoveryRequestedView(RecoveryPrivacyMixin,View):
    def get(self,request):
        return render(request,'accounts/recovery_requested.html',{'notice':recovery.GENERIC_NOTICE})


class UsernameTokenEntryView(RecoveryPrivacyMixin,View):
    token_entry=True

    def get(self,request,token):
        from django.core import signing
        try:
            signing.loads(token,salt='snp-username-recovery',max_age=getattr(settings,'ACCOUNT_RECOVERY_TIMEOUT',1800))
            request.session['username_recovery_proof']=token
        except signing.BadSignature:
            request.session.pop('username_recovery_proof',None)
        return redirect('username_recovery_confirm')


class UsernameConfirmView(RecoveryPrivacyMixin,View):
    def get(self,request):
        # Scanners can stage a link, but only a CSRF-protected POST consumes it.
        present=bool(request.session.get('username_recovery_proof'))
        return render(request,'accounts/username_confirm.html',{'confirmation':present,'invalid':not present})

    def post(self,request):
        token=request.session.pop('username_recovery_proof','')
        try:
            names=recovery.consume_username_token(token)
        except Exception:
            logger.error('Recovery proof storage unavailable.')
            names=None
        return render(request,'accounts/username_confirm.html',{'usernames':names or [],'invalid':not names})


class PasswordConfirmView(RecoveryPrivacyMixin,PasswordResetConfirmView):
    template_name='accounts/password_confirm.html'
    success_url=reverse_lazy('password_reset_complete')
    post_reset_login=False

    def get_user(self, uidb64):
        user=super().get_user(uidb64)
        return user if user and user.is_active and user.has_usable_password() else None


class PasswordCompleteView(RecoveryPrivacyMixin,PasswordResetCompleteView):
    template_name='accounts/password_complete.html'
