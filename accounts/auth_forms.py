"""Authentication feedback without relaxing the approval policy."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class ApprovalAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            user = get_user_model()._default_manager.filter(**{get_user_model().USERNAME_FIELD: username}).first()
            from .rbac import account_can_login
            if user and not account_can_login(user):
                # Verify without a setter: even a legacy inactive hash is preserved.
                from django.contrib.auth.hashers import check_password
                if check_password(password, user.password):
                    raise ValidationError('관리자 승인 대기 중이거나 사용이 중지된 계정입니다. 관리자에게 승인 상태를 확인해 주세요.', code='inactive')
                raise self.get_invalid_login_error()
        return super().clean()



class RecoveryEmailForm(forms.Form):
    email = forms.EmailField(label='가입 이메일', max_length=254, widget=forms.EmailInput(attrs={'autocomplete':'email','class':'form-control'}))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
