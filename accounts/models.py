from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', '관리자'
        NUTRITIONIST = 'NUTRITIONIST', '영양사'
        SUPPLIER = 'SUPPLIER', '발주처'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.NUTRITIONIST
    )
    class AccountState(models.TextChoices):
        PENDING = 'PENDING', '승인 대기'
        ACTIVE = 'ACTIVE', '승인 완료'
        SUSPENDED = 'SUSPENDED', '관리자 정지'
        DISABLED = 'DISABLED', '비활성화'
        WITHDRAWN = 'WITHDRAWN', '탈퇴'
        LEGACY_INACTIVE = 'LEGACY_INACTIVE', '기존 상태 확인 필요'

    account_state = models.CharField(max_length=20, choices=AccountState.choices, default=AccountState.LEGACY_INACTIVE)
    rbac_managed = models.BooleanField(default=False)
    access_revision = models.PositiveIntegerField(default=0)

    name = models.CharField(max_length=50, help_text="사용자명 또는 업체명")
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"[{self.get_role_display()}] {self.name or self.username}"

class AccessPolicy(models.Model):
    """Singleton mutex and audited mirror; the environment remains authoritative."""
    mode = models.CharField(max_length=10, default='manual')


class AccessAudit(models.Model):
    actor = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='access_actions')
    target = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='access_history')
    actor_label = models.CharField(max_length=150, default='SYSTEM')
    target_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=80)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    result = models.CharField(max_length=10, default='SUCCESS')
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pk']


class AdminRoleRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='admin_role_request')
    reason = models.TextField(max_length=1000)
    status = models.CharField(max_length=12, choices=[('PENDING','승인 대기'),('APPROVED','승인'),('REJECTED','거절')], default='PENDING')
    revision = models.PositiveIntegerField(default=0)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='reviewed_admin_requests')
    decision_note = models.CharField(max_length=500, blank=True)


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    message = models.TextField(max_length=2000)
    active = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
