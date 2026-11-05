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

class CustomLogoutView(LogoutView):
    # next_page=reverse("home")
    next_page=reverse_lazy("home")

User=get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="이메일", required=True, max_length=254, widget=forms.EmailInput(attrs={"class":"form-control","autocomplete":"email"}))

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
            register(user)
        return user


class SignUpView(CreateView):
    form_class=SignUpForm
    template_name="accounts/signup.html"
    # success_url=reverse("login")
    success_url=reverse_lazy("login")
    

    def form_valid(self, form):
        from .rbac import approval_mode
        messages.info(self.request, '가입이 완료되었습니다. 바로 로그인할 수 있습니다.' if approval_mode()=='auto' else '가입 신청이 접수되었습니다. 관리자 승인 후 로그인할 수 있습니다.')
        return super().form_valid(form)
