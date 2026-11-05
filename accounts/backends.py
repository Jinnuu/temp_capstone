from django.contrib.auth.backends import ModelBackend
from .rbac import account_can_login


class ApprovalBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return account_can_login(user)
