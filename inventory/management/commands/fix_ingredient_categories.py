from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import Q
from inventory.models import Ingredient


class Command(BaseCommand):
    help = "오분류된 식자재 카테고리 일괄 정정 및 납품업체 재매핑 스크립트"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== 식자재 카테고리 일괄 정정 시작 ==="))

        category_rules = {
            "농산물": [
                "배추", "무", "양파", "마늘", "파", "대파", "쪽파", "고추", "풋고추", "청양고추",
                "당근", "감자", "고구마", "호박", "애호박", "오이", "상추", "시금치", "버섯", "팽이버섯",
                "표고버섯", "새송이버섯", "토마토", "사과", "배", "포도", "바나나", "콩나물", "숙주",
                "부추", "깻잎", "가지", "피망", "파프리카", "양배추", "쌈채소", "생강", "미나리",
                "달래", "쑥갓", "우엉", "연근", "더덕", "도라지", "청경채", "아욱", "근대"
            ],
            "곡류": [
                "쌀", "현미", "보리", "찹쌀", "잡곡", "콩", "대두", "서리태", "팥", "조", "수수", "차조", "옥수수", "밀가루", "전분"
            ],
            "육류": [
                "돼지", "돈육", "소고기", "우육", "한우", "수입육", "삼겹살", "목살", "양지", "사골", "갈비", "등심", "안심", "잡육", "제육"
            ],
            "계육 및 계란": [
                "닭", "계육", "닭고기", "닭가슴살", "닭다리", "오리", "계란", "달걀", "전란"
            ],
            "김치": [
                "김치", "깍두기", "겉절이", "동치미", "백김치", "열무김치", "파김치", "석박지"
            ],
            "유제품": [
                "우유", "분유", "치즈", "버터", "생크림", "요거트", "요구르트", "발효유"
            ],
            "공산품": [
                "식용유", "참기름", "들기름", "간장", "된장", "고추장", "쌈장", "소금", "설탕", "후추",
                "식초", "물엿", "올리고당", "카레", "짜장", "당면", "국수", "사리", "햄", "소세지",
                "참치", "스팸", "어묵", "맛살", "만두", "떡", "빵", "시리얼"
            ],
        }

        total_updated = 0

        for target_category, keywords in category_rules.items():
            q_objects = Q()
            for kw in keywords:
                q_objects |= Q(name__icontains=kw)

            qs = Ingredient.objects.filter(q_objects).exclude(category=target_category)
            count = qs.count()

            if count > 0:
                updated = qs.update(category=target_category)
                total_updated += updated
                self.stdout.write(
                    self.style.SUCCESS(f"  [정정] 키워드 매핑 -> '{target_category}' ({updated}건 업데이트)")
                )

        self.stdout.write(self.style.SUCCESS(f"=== 총 {total_updated}건의 식자재 카테고리가 일괄 정정되었습니다. ==="))

        self.stdout.write(self.style.WARNING("=== 카테고리 정정에 따른 납품업체 자동 재매핑 실행중... ==="))
        try:
            call_command("assign_suppliers")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"납품업체 재매핑 중 오류 발생: {e}"))
