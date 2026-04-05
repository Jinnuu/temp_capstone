from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.urls import reverse
from django.views.generic import CreateView
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

class CustomLogoutView(LogoutView):
    # next_page=reverse("home")
    next_page=reverse_lazy("home")

User=get_user_model()

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)

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

class SignUpView(CreateView):
    form_class=SignUpForm
    template_name="accounts/signup.html"
    # success_url=reverse("login")
    success_url=reverse_lazy("login")
    
