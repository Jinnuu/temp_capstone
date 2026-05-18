from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from meals.models import DietPlan
from inventory.models import InventoryLog, Ingredient
# 🔥 실제 forecasting 앱의 위치에 맞춰 import 하세요.
from forecasting.models import AttendancePrediction 

class Command(BaseCommand):
    help = '예측 모델의 인원수를 기반으로 식재료 출고 로그를 생성하여 재고를 차감합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='특정 날짜 수동 처리 (YYYY-MM-DD)')

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. 날짜 설정
        date_str = options.get('date')
        if date_str:
            target_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
            
        # 2. 해당 날짜의 미처리 식단 조회
        plans = DietPlan.objects.filter(target_date=target_date, is_served=False)
        
        if not plans.exists():
            self.stdout.write(self.style.WARNING(f"{target_date}에 처리할 식단이 없거나 이미 차감 완료되었습니다."))
            return

        # 3. 식단(한글)과 예측모델(영문) 끼니 이름 매핑
        meal_type_map = {
            "조식": "breakfast",
            "중식": "lunch",
            "석식": "dinner"
        }
            
        count = 0
        for plan in plans:
            # 4. 예측 데이터 테이블 조회 (forecasting_attendanceprediction)
            eng_meal_type = meal_type_map.get(plan.meal_type)
            prediction = AttendancePrediction.objects.filter(
                prediction_date=target_date, 
                meal_type=eng_meal_type
            ).first()

            # 5. 인원수 결정 로직 (예측값 우선 -> 없으면 수동 입력값)
            if prediction:
                final_headcount = prediction.predicted_count
                description_tag = f"예측 모델({prediction.model_name}) 기반"
            else:
                final_headcount = plan.headcount
                description_tag = "수동 입력 기반"

            # 인원수가 0이면 로그를 남기지 않고 스킵
            if final_headcount <= 0:
                self.stdout.write(self.style.NOTICE(f"{plan.meal_type} 식단: 최종 인원수가 0명이라 건너뜁니다."))
                continue
                
            # 6. 재고 출고 로그(InventoryLog) 생성
            # 현재고 속성이 없으므로 OUT 로그를 쌓아 계산에 반영되게 함
            for diet_menu in plan.diet_menus.all():
                for recipe in diet_menu.menu.recipes.all():
                    ing = recipe.ingredient
                    used_qty = recipe.required_amount * final_headcount
                    
                    # 수치 계산 로직 없이 로그 객체만 생성
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type=InventoryLog.LogType.OUT, # '출고' 타입
                        quantity=used_qty,
                        description=f"{target_date} {plan.meal_type} {description_tag} 차감 ({final_headcount}명)"
                    )
            
            # 7. 식단 처리 완료 표시
            plan.is_served = True
            plan.save()
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f"{target_date} 기준 총 {count}개 식단의 재고 로그 생성이 완료되었습니다."))