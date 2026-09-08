from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from inventory.models import Ingredient
from procurement.models import PurchaseOrder

User = get_user_model()

class Command(BaseCommand):
    help = '기존 납품업체 계정 및 연관 데이터를 안전하게 정리하고 카테고리별 규정에 맞춰 납품업체를 재매핑합니다.'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.NOTICE("납품업체 초기화 및 재매핑 작업을 시작합니다..."))

            # 1. 카테고리별 납품업체 매핑 정의
            supplier_definitions = [
                {
                    'name': '신선유통',
                    'username': 'sinseon',
                    'categories': ['가공식품', '간식', '공산품', '양념류']
                },
                {
                    'name': '다나푸드',
                    'username': 'danafood',
                    'categories': ['계육 및 계란', '계육', '계란']
                },
                {
                    'name': '하나유통',
                    'username': 'hanafood',
                    'categories': ['곡류']
                },
                {
                    'name': '일오삼',
                    'username': '153food',
                    'categories': ['육류', '수산물']
                },
                {
                    'name': '해동',
                    'username': 'haedong',
                    'categories': ['농산물', '농산품', '채소류']
                },
                {
                    'name': '행복한식자재',
                    'username': 'happyfood',
                    'categories': ['유제품', '행복한 식자재', '행복한식자재']
                },
                {
                    'name': '구전식품',
                    'username': 'gujeon',
                    'categories': ['김치', '김치류']
                },
            ]

            # 2. 신규/지정 납품업체 계정 생성 및 확보 (관리자 계정 제외)
            supplier_users = {}
            whitelist_user_ids = []
            whitelist_names = [item['name'] for item in supplier_definitions]
            whitelist_usernames = [item['username'] for item in supplier_definitions]

            for item in supplier_definitions:
                s_name = item['name']
                s_uname = item['username']

                # username 또는 name으로 기존 유저 탐색
                user = None
                query_by_name = Q()
                if hasattr(User, 'name'):
                    query_by_name = Q(name=s_name)
                elif hasattr(User, 'first_name'):
                    query_by_name = Q(first_name=s_name)

                # 하나유통 / 하나푸드 호환 검색
                if s_name == '하나유통':
                    if hasattr(User, 'name'):
                        query_by_name |= Q(name='하나푸드')
                    elif hasattr(User, 'first_name'):
                        query_by_name |= Q(first_name='하나푸드')

                if query_by_name:
                    user = User.objects.filter(Q(username=s_uname) | query_by_name).first()
                else:
                    user = User.objects.filter(username=s_uname).first()

                if not user:
                    user = User(username=s_uname, is_staff=False, is_superuser=False)
                    if hasattr(user, 'name'):
                        setattr(user, 'name', s_name)
                    user.save()
                    self.stdout.write(f"신규 납품업체 계정 생성: {s_name} ({s_uname})")
                else:
                    if hasattr(user, 'name') and getattr(user, 'name') != s_name:
                        setattr(user, 'name', s_name)
                        user.save()
                    self.stdout.write(f"기존 납품업체 계정 확인: {s_name} ({s_uname})")

                supplier_users[s_name] = user
                whitelist_user_ids.append(user.id)

            # 3. 방어 로직: 기존 식재료 데이터의 supplier 연결 해제 (SET NULL 방어)
            ingredient_reset_count = Ingredient.objects.update(supplier=None)
            self.stdout.write(f"식재료-기존업체 외래키 끊기 완료: {ingredient_reset_count}건")

            # 4. 강력한 화이트리스트(Whitelist) 기반 더미 계정 강제 삭제 로직
            # - is_superuser=True 인 최고 관리자 계정 제외
            # - 7개 공식 화이트리스트 명단(username/name 기준) 제외
            # - 그 외에 남은 모든 User 객체는 무조건 delete() 호출하여 영구 삭제
            whitelist_q = Q(id__in=whitelist_user_ids) | Q(username__in=whitelist_usernames) | Q(username='hanafood')
            if hasattr(User, 'name'):
                whitelist_q |= Q(name__in=whitelist_names) | Q(name='하나푸드')
            if hasattr(User, 'first_name'):
                whitelist_q |= Q(first_name__in=whitelist_names) | Q(first_name='하나푸드')

            users_to_delete = User.objects.exclude(is_superuser=True).exclude(whitelist_q).distinct()

            # 삭제 대상 계정과 연결되어 있는 PurchaseOrder가 있다면 지정된 대표 업체로 안전 이전 (CASCADE 연쇄 삭제 방지)
            default_supplier = supplier_users['신선유통']
            po_reassigned = PurchaseOrder.objects.filter(supplier__in=users_to_delete).update(supplier=default_supplier)
            if po_reassigned > 0:
                self.stdout.write(f"발주(PurchaseOrder) 연쇄 삭제 방지를 위해 {po_reassigned}건의 발주서를 기본 대표업체로 재연결했습니다.")

            # 5. 기존 더미 납품업체 계정 완벽 강제 삭제
            deleted_count, _ = users_to_delete.delete()
            self.stdout.write(self.style.WARNING(f"더미 납품업체 계정 총 {deleted_count}개 완전 삭제 완료."))

            # 6. 카테고리 매핑 규칙에 따라 식재료에 신규 업체 매핑
            total_mapped = 0
            for item in supplier_definitions:
                s_name = item['name']
                supplier_user = supplier_users[s_name]
                cats = item['categories']

                q_cat = Q()
                for c in cats:
                    q_cat |= Q(category__icontains=c)

                updated = Ingredient.objects.filter(q_cat).update(supplier=supplier_user)
                total_mapped += updated
                self.stdout.write(f"  - [{s_name}] 카테고리({', '.join(cats)}) => {updated}개 식재료 매핑 완료")

            # 7. 발주서(PurchaseOrder) 데이터의 supplier를 매핑된 품목 기준으로 정교하게 재동기화
            po_resynced = 0
            for po in PurchaseOrder.objects.all():
                first_item = po.items.select_related('ingredient__supplier').first()
                if first_item and first_item.ingredient and first_item.ingredient.supplier:
                    if po.supplier != first_item.ingredient.supplier:
                        po.supplier = first_item.ingredient.supplier
                        po.save()
                        po_resynced += 1

            if po_resynced > 0:
                self.stdout.write(f"발주서 {po_resynced}건의 납품업체 정보를 품목 기준에 맞춰 재동기화했습니다.")

            self.stdout.write(self.style.SUCCESS("✓ 모든 납품업체 초기화 및 카테고리 재매핑 작업이 성공적으로 완료되었습니다."))
