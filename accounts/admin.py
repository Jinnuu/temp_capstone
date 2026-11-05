"""Account access changes use the audited application console, not raw field edits."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import User, AccessAudit, AccessPolicy


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'name', 'role', 'account_state', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('추가 정보', {'fields': ('role', 'name', 'phone_number', 'account_state')}),)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(Group)
@admin.register(Group)
class ProtectedGroupAdmin(GroupAdmin):
    def has_change_permission(self, request, obj=None): return False
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
