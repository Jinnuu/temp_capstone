from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.urls import reverse
from django.views.generic import CreateView
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django import forms
from .auth_forms import ApprovalAuthenticationForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = ApprovalAuthenticationForm

    def get_success_url(self):
        explicit = self.get_redirect_url()
        if explicit:
            return explicit
        from .workspaces import landing_url
        return landing_url(self.request.user)

class CustomLogoutView(LogoutView):
    # next_page=reverse("home")
    next_page=reverse_lazy("home")

User=get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="이메일", required=True, max_length=254, widget=forms.EmailInput(attrs={"class":"form-control","autocomplete":"email"}))

    signup_type = forms.ChoiceField(label='가입 유형', choices=[('DIETITIAN','영양사로 가입'),('SUPPLIER','공급업체로 가입')], required=False, initial='DIETITIAN', widget=forms.RadioSelect)
    company_name = forms.CharField(label='업체명', max_length=100, required=False)
    contact_name = forms.CharField(label='담당자', max_length=50, required=False)
    contact_phone = forms.CharField(label='연락처', max_length=30, required=False)

    def clean_signup_type(self):
        return self.cleaned_data.get('signup_type') or 'DIETITIAN'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('signup_type') == 'SUPPLIER':
            for key in ('company_name','contact_name','contact_phone'):
                if not (cleaned.get(key) or '').strip():
                    self.add_error(key,'공급업체 가입 시 필수 항목입니다.')
        return cleaned

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "아이디를 입력하세요",
        })
        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "비밀번호를 입력하세요",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "비밀번호를 다시 입력하세요",
        })

        self.fields["username"].help_text = ""
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.name = user.username[:50]
        user.is_active = False
        if commit:
            from .access_service import register
            from django.db import transaction
            with transaction.atomic():
                kind = self.cleaned_data.get('signup_type', 'DIETITIAN')
                user.role = 'SUPPLIER' if kind == 'SUPPLIER' else 'NUTRITIONIST'
                if kind=='SUPPLIER':user.name=self.cleaned_data['company_name'].strip()[:50]
                register(user, kind)
                if kind == 'SUPPLIER':
                    from procurement.models import SupplierMembership
                    SupplierMembership.objects.create(account=user, registered_via_portal=True, requested_company=' '.join(self.cleaned_data['company_name'].split()), contact_name=self.cleaned_data['contact_name'].strip(), contact_phone=self.cleaned_data['contact_phone'].strip())
        return user


class SignUpView(CreateView):
    form_class=SignUpForm
    template_name="accounts/signup.html"
    # success_url=reverse("login")
    success_url=reverse_lazy("login")
    

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.info(self.request, '가입이 완료되었습니다. 바로 로그인할 수 있습니다.' if self.object.is_active else '가입 신청이 접수되었습니다. 관리자 승인 후 로그인할 수 있습니다.')
        return response
