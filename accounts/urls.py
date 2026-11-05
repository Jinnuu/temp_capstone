from django.urls import path
from .views import CustomLoginView, CustomLogoutView, SignUpView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("signup/", SignUpView.as_view(), name="signup"),
]
from .recovery_views import (UsernameRequestView,PasswordRequestView,RecoveryRequestedView,UsernameConfirmView,UsernameTokenEntryView,PasswordConfirmView,PasswordCompleteView)
urlpatterns += [
    path('recovery/username/',UsernameRequestView.as_view(),name='username_recovery'),
    path('recovery/password/',PasswordRequestView.as_view(),name='password_reset'),
    path('recovery/requested/',RecoveryRequestedView.as_view(),name='recovery_requested'),
    path('recovery/username/confirm/',UsernameConfirmView.as_view(),name='username_recovery_confirm'),
    path('recovery/username/confirm/<str:token>/',UsernameTokenEntryView.as_view(),name='username_confirm'),
    path('recovery/reset/done/',PasswordCompleteView.as_view(),name='password_reset_complete'),
    path('recovery/reset/<uidb64>/<token>/',PasswordConfirmView.as_view(),name='password_reset_confirm'),
]
