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
    name = models.CharField(max_length=50, help_text="사용자명 또는 업체명")
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"[{self.get_role_display()}] {self.name or self.username}"