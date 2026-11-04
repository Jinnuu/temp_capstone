import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from forecasting.models import AttendancePrediction
from inventory.models import Ingredient, InventoryLog
from meals.models import DietMenu, DietPlan, Menu, Recipe
from procurement.models import OrderItem, PurchaseOrder


class Command(BaseCommand):
    help = "E2E 업무 프로세스 1~9단계 시연을 위한 테스트 데이터를 DB에 구축합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            default="2026-09-07",
            help="테스트 주간 시작일 (월요일, 형식: YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        start_date_str = options["start_date"]
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date(2026, 9, 7)

        # Make sure start_date is Monday
        start_date = start_date - timedelta(days=start_date.weekday())
        end_date = start_date + timedelta(days=6)

        self.stdout.write(
            self.style.WARNING(
                f"\n🚀 E2E 워크플로우 1~9단계 테스트 데이터 생성을 시작합니다... (주간: {start_date} ~ {end_date})"
            )
        )

        with transaction.atomic():
            User = get_user_model()

            # -------------------------------------------------------------
            # 1. 납품업체 (User) 세팅
            # -------------------------------------------------------------
            suppliers_data = [
                {"username": "cj_freshway", "name": "CJ프레시웨이"},
                {"username": "hyundai_greenfood", "name": "현대그린푸드"},
                {"username": "dongwon_homefood", "name": "동원홈푸드"},
            ]

            suppliers = {}
            for sdata in suppliers_data:
                user, _ = User.objects.get_or_create(
                    username=sdata["username"],
                    defaults={"is_staff": False, "is_active": True},
                )
                if hasattr(user, "name") and not user.name:
                    user.name = sdata["name"]
                    user.save()
                suppliers[sdata["name"]] = user

            # -------------------------------------------------------------
            # 2. 식재료 마스터 세팅
            # -------------------------------------------------------------
            ingredients_info = [
                # 곡류 (CJ프레시웨이)
                {"name": "백미(국산)", "spec": "20kg/포", "unit": "kg", "price": 3200, "safe": 50, "cat": "곡류", "sup": "CJ프레시웨이"},
                # 육류 (CJ프레시웨이)
                {"name": "돼지고기(전지)", "spec": "냉장/kg", "unit": "kg", "price": 14500, "safe": 30, "cat": "육류", "sup": "CJ프레시웨이"},
                {"name": "쇠고기(양지)", "spec": "냉장/kg", "unit": "kg", "price": 28000, "safe": 15, "cat": "육류", "sup": "CJ프레시웨이"},
                {"name": "닭고기(정육)", "spec": "냉동/kg", "unit": "kg", "price": 11000, "safe": 20, "cat": "육류", "sup": "CJ프레시웨이"},
                # 수산물 (동원홈푸드)
                {"name": "오징어(손질)", "spec": "냉동/kg", "unit": "kg", "price": 9000, "safe": 10, "cat": "수산물", "sup": "동원홈푸드"},
                {"name": "고등어(자반)", "spec": "냉동/kg", "unit": "kg", "price": 8500, "safe": 10, "cat": "수산물", "sup": "동원홈푸드"},
                # 채소류 (현대그린푸드)
                {"name": "양파", "spec": "15kg/망", "unit": "kg", "price": 2400, "safe": 20, "cat": "채소류", "sup": "현대그린푸드"},
                {"name": "대파", "spec": "1kg/단", "unit": "kg", "price": 3200, "safe": 10, "cat": "채소류", "sup": "현대그린푸드"},
                {"name": "무", "spec": "20kg/박스", "unit": "kg", "price": 1800, "safe": 15, "cat": "채소류", "sup": "현대그린푸드"},
                {"name": "배추김치", "spec": "10kg/박스", "unit": "kg", "price": 4500, "safe": 30, "cat": "김치", "sup": "현대그린푸드"},
                # 양념류 (동원홈푸드)
                {"name": "고추장", "spec": "14kg/통", "unit": "kg", "price": 6500, "safe": 5, "cat": "양념류", "sup": "동원홈푸드"},
                {"name": "간장", "spec": "18L/통", "unit": "kg", "price": 4200, "safe": 5, "cat": "양념류", "sup": "동원홈푸드"},
            ]

            ing_objs = {}
            for item in ingredients_info:
                ing, _ = Ingredient.objects.get_or_create(
                    name=item["name"],
                    defaults={
                        "spec": item["spec"],
                        "unit": item["unit"],
                        "unit_price": item["price"],
                        "safe_stock_level": Decimal(str(item["safe"])),
                        "category": item["cat"],
                        "supplier": suppliers[item["sup"]],
                    },
                )
                ing_objs[item["name"]] = ing

            # -------------------------------------------------------------
            # 3. 메뉴 및 레시피 세팅
            # -------------------------------------------------------------
            menus_info = [
                {"name": "쌀밥", "cat": "밥", "recipes": [("백미(국산)", "0.15")]},
                {"name": "소고기미역국", "cat": "국", "recipes": [("쇠고기(양지)", "0.04"), ("간장", "0.005")]},
                {"name": "콩나물국", "cat": "국", "recipes": [("무", "0.03"), ("대파", "0.01")]},
                {"name": "돼지불고기", "cat": "주반찬", "recipes": [("돼지고기(전지)", "0.15"), ("양파", "0.03"), ("대파", "0.01"), ("간장", "0.01")]},
                {"name": "닭갈비", "cat": "주반찬", "recipes": [("닭고기(정육)", "0.16"), ("양파", "0.04"), ("고추장", "0.02")]},
                {"name": "오징어볶음", "cat": "주반찬", "recipes": [("오징어(손질)", "0.12"), ("양파", "0.03"), ("대파", "0.01"), ("고추장", "0.015")]},
                {"name": "고등어구이", "cat": "주반찬", "recipes": [("고등어(자반)", "0.15")]},
                {"name": "배추김치", "cat": "김치", "recipes": [("배추김치", "0.05")]},
            ]

            menu_objs = {}
            for mdata in menus_info:
                menu, _ = Menu.objects.get_or_create(
                    name=mdata["name"],
                    defaults={"category": mdata["cat"]},
                )
                menu_objs[mdata["name"]] = menu

                for ing_name, req_amt in mdata["recipes"]:
                    Recipe.objects.get_or_create(
                        menu=menu,
                        ingredient=ing_objs[ing_name],
                        defaults={"required_amount": Decimal(req_amt)},
                    )

            # -------------------------------------------------------------
            # 4. 주간 식단(DietPlan) & 식수 예측(AttendancePrediction) 세팅
            # -------------------------------------------------------------
            meal_patterns = {
                "조식": (["쌀밥", "콩나물국", "배추김치"], 150, "breakfast"),
                "중식": (["쌀밥", "소고기미역국", "돼지불고기", "배추김치"], 350, "lunch"),
                "석식": (["쌀밥", "콩나물국", "닭갈비", "배추김치"], 200, "dinner"),
            }

            curr = start_date
            while curr <= end_date:
                for mtype, (m_names, base_hc, pred_key) in meal_patterns.items():
                    # DietPlan
                    plan, _ = DietPlan.objects.get_or_create(
                        target_date=curr,
                        meal_type=mtype,
                        defaults={"headcount": base_hc, "is_served": True},
                    )

                    for m_name in m_names:
                        DietMenu.objects.get_or_create(
                            diet_plan=plan,
                            menu=menu_objs[m_name],
                        )

                    # AttendancePrediction
                    AttendancePrediction.objects.get_or_create(
                        prediction_date=curr,
                        meal_type=pred_key,
                        defaults={
                            "predicted_count": base_hc + random.randint(-5, 10),
                            "model_name": "LightGBM_Ensemble_v2",
                        },
                    )

                curr += timedelta(days=1)

            # -------------------------------------------------------------
            # 5. 발주(PurchaseOrder) & 발주상세(OrderItem) 생성 (Step 4~7)
            # -------------------------------------------------------------
            for day_idx in range(5):  # 월~금
                order_date = start_date + timedelta(days=day_idx)

                for sup_name, sup_user in suppliers.items():
                    po, _ = PurchaseOrder.objects.get_or_create(
                        supplier=sup_user,
                        status=PurchaseOrder.Status.DELIVERED,
                        defaults={"total_amount": 0},
                    )

                    # Supplier ingredients
                    sup_ings = [ing for ing in ing_objs.values() if ing.supplier == sup_user]
                    po_total = 0

                    for ing in sup_ings:
                        req_q = Decimal(str(random.randint(20, 80)))
                        item_price = int(req_q * Decimal(str(ing.unit_price)))
                        po_total += item_price

                        OrderItem.objects.get_or_create(
                            purchase_order=po,
                            ingredient=ing,
                            target_date=order_date,
                            meal_type="중식",
                            defaults={
                                "required_qty": req_q,
                                "missing_qty": req_q,
                                "order_unit_price": ing.unit_price,
                                "estimated_price": item_price,
                            },
                        )

                    po.total_amount = po_total
                    po.save()

            # -------------------------------------------------------------
            # 6. 재고 수불 기록(InventoryLog) 세팅 (Step 8)
            # -------------------------------------------------------------
            for ing in ing_objs.values():
                base_time = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

                # 1) 입고
                InventoryLog.objects.get_or_create(
                    ingredient=ing,
                    log_type=InventoryLog.LogType.IN,
                    quantity=Decimal("100.00"),
                    transaction_date=base_time + timedelta(hours=8),
                    defaults={"description": "시연용 E2E 초기 입고"},
                )

                # 2) 출고 (급식 소요)
                InventoryLog.objects.get_or_create(
                    ingredient=ing,
                    log_type=InventoryLog.LogType.OUT,
                    quantity=Decimal("45.50"),
                    transaction_date=base_time + timedelta(days=2, hours=14),
                    defaults={"description": "조/중/석식 메뉴 조리 출고"},
                )

                # 3) 조정 (수불 정산)
                InventoryLog.objects.get_or_create(
                    ingredient=ing,
                    log_type=InventoryLog.LogType.ADJ,
                    quantity=Decimal("2.00"),
                    transaction_date=base_time + timedelta(days=4, hours=17),
                    defaults={"description": "주간 재고 실사 차이 조정입고"},
                )

        self.stdout.write(self.style.SUCCESS("\n✅ E2E 테스트 데이터 구축이 완벽하게 완료되었습니다!"))

        # -------------------------------------------------------------
        # 7. 1~9단계 접속 URL 시연 가이드 출력
        # -------------------------------------------------------------
        guide_text = f"""
================================================================================
  📌 [S&P 급식 관리 시스템 실무 프로세스 1~9단계 E2E 시연 가이드]
  테스트 대상 주간: {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')}
================================================================================

1단계 [식단 작성]:
  - 월간 식단표 뷰:      http://127.0.0.1:8000/meals/monthly/
  - 주간 식단 작성:      http://127.0.0.1:8000/meals/weekly/

2단계 [식수 예측]:
  - AI 식수 예측 관리:   http://127.0.0.1:8000/forecasting/

3단계 [스마트 발주 수량 자동 계산]:
  - 식단/재고 연동 발주: http://127.0.0.1:8000/procurement/create-smart/?start_date={start_date}&end_date={start_date + timedelta(days=4)}

4단계 [발주서 생성 및 전송]:
  - 발주서 목록:        http://127.0.0.1:8000/procurement/orders/

5단계 [실무 양식 - 급식물품 구입요구서]:
  - 구입요구서 (A4 인쇄): http://127.0.0.1:8000/procurement/docs/purchase-requisition/?start_date={start_date}&end_date={start_date + timedelta(days=4)}

6단계 [주간 / 업체별 발주 명세서]:
  - 업체별 발주서 (A4):   http://127.0.0.1:8000/procurement/vendor-report/?start_date={start_date}&end_date={start_date + timedelta(days=4)}

7단계 [입고 검수 및 검수일지 작성]:
  - 일일 검수서 (A4):     http://127.0.0.1:8000/procurement/docs/inspection-log/?date={start_date}

8단계 [재료 수불 현황 및 재고 관리]:
  - 수불현황 및 재고조정: http://127.0.0.1:8000/inventory/

9단계 [월말 정산 (총 식자재 소요량 및 금액 정산)]:
  - 월말 정산 보고서(A4): http://127.0.0.1:8000/procurement/docs/monthly-settlement/?month={start_date.strftime('%Y-%m')}

================================================================================
"""
        self.stdout.write(guide_text)
