from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q
from inventory.models import Ingredient

User = get_user_model()

class Command(BaseCommand):
    help = '식재료 대분류(category)별 전담 납품업체 일괄 자동 매핑'

    def handle(self, *args, **options):
        # 카테고리별 납품업체 매핑 정의
        mapping_rules = {
            '행복한식자재': ['유제품'],
            '해동': ['농산물'],
            '신선유통': ['공산품'],
            '다나푸드': ['계육및계란', '계육 및 계란', '계육', '계란'],
            '하나유통': ['곡류'],
            '구전식품': ['김치'],
            '일오삼': ['육류'],
        }

        self.stdout.write(self.style.SUCCESS("=== 카테고리별 납품업체 자동 매핑 시작 ==="))

        total_updated_ingredients = 0

        for supplier_name, categories in mapping_rules.items():
            # 1. 납품업체(User) 계정 get_or_create
            supplier_user, created = User.objects.get_or_create(
                username=supplier_name,
                defaults={
                    'is_active': True,
                }
            )
            
            action_str = "생성됨" if created else "조회됨"
            self.stdout.write(f"-> 납품업체 계정 [{supplier_name}] ({action_str})")

            # 2. 카테고리 조건 검색 (icontains 활용하여 띄어쓰기 유연 처리)
            q_objects = Q()
            for cat in categories:
                q_objects |= Q(category__icontains=cat)

            target_qs = Ingredient.objects.filter(q_objects)
            count = target_qs.count()

            # 3. 일괄 업데이트 (bulk update)
            if count > 0:
                updated_count = target_qs.update(supplier=supplier_user)
                total_updated_ingredients += updated_count
                self.stdout.write(
                    self.style.SUCCESS(f"   [매핑 완료] 카테고리 {categories} -> {supplier_name} ({updated_count}건 업데이트)")
                )
            else:
                self.stdout.write(f"   [건너뜀] 카테고리 {categories}에 해당하는 식재료 품목이 없습니다.")

        self.stdout.write(
            self.style.SUCCESS(f"\n=== 매핑 완료: 총 {total_updated_ingredients}개 식재료 품목 납품업체 매핑 완료 ===")
        )
