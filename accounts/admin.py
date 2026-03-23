from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 관리자 목록 화면에서 역할(role)과 이름도 보이게 추가
    list_display = ('username', 'name', 'role', 'email', 'is_staff')
    
    # 상세 수정 화면에 필드 추가
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('role', 'name', 'phone_number')}),
    )