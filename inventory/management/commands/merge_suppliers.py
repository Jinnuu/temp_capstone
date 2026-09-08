from collections import defaultdict
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from inventory.models import Ingredient
from procurement.models import PurchaseOrder


class Command(BaseCommand):
    help = "중복 생성된 납품업체(User) 계정을 하나로 병합하고 연관 데이터를 이관한 후 중복 계정을 정리하는 커맨드"

    def handle(self, *args, **options):
        User = get_user_model()

        # 1. 화면에 표시되는 이름(name 필드 값이 있으면 name, 없으면 username)을 기준으로 계정 그룹화
        users_by_display_name = defaultdict(list)
        for user in User.objects.all().order_by('id'):
            display_name = getattr(user, 'name', None)
            if display_name and str(display_name).strip():
                name_key = str(display_name).strip()
            else:
                name_key = str(user.username).strip()
            users_by_display_name[name_key].append(user)

        merged_groups_count = 0
        total_deleted_users = 0

        # 2. 트랜잭션 원자성을 적용하여 안전하게 데이터 이관 및 중복 계정 삭제
        with transaction.atomic():
            for display_name, users in users_by_display_name.items():
                if len(users) < 2:
                    continue

                merged_groups_count += 1
                # ID가 가장 작은 계정을 '원본(Primary)'으로 지정
                primary_user = users[0]
                duplicate_users = users[1:]
                duplicate_ids = [u.id for u in duplicate_users]

                self.stdout.write(
                    self.style.WARNING(
                        f"\n[중복 발견] 표시 이름: '{display_name}' (총 {len(users)}개 계정)"
                    )
                )
                self.stdout.write(
                    f"  - 원본 계정 (Primary): ID={primary_user.id}, username='{primary_user.username}'"
                )
                for dup in duplicate_users:
                    self.stdout.write(
                        f"  - 중복 계정 (Duplicate): ID={dup.id}, username='{dup.username}'"
                    )

                # 연관 데이터 이관
                # 식재료(Ingredient.supplier) 이관
                ing_updated = Ingredient.objects.filter(supplier_id__in=duplicate_ids).update(supplier=primary_user)
                
                # 발주서(PurchaseOrder.supplier) 이관
                po_updated = PurchaseOrder.objects.filter(supplier_id__in=duplicate_ids).update(supplier=primary_user)

                self.stdout.write(
                    f"  -> 식재료(Ingredient) supplier 이관: {ing_updated}건"
                )
                self.stdout.write(
                    f"  -> 발주서(PurchaseOrder) supplier 이관: {po_updated}건"
                )

                # 중복 계정 삭제
                deleted_count = 0
                for dup in duplicate_users:
                    dup.delete()
                    deleted_count += 1

                total_deleted_users += deleted_count
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> 중복 계정 {deleted_count}개 삭제 완료"
                    )
                )

        if merged_groups_count == 0:
            self.stdout.write(self.style.SUCCESS("\n중복된 납품업체 계정이 존재하지 않습니다."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[정리 완료] 총 {merged_groups_count}개 그룹에서 중복 계정 {total_deleted_users}개가 원본 계정으로 병합 및 삭제되었습니다."
                )
            )
