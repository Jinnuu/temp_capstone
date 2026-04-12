from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from meals.models import DietPlan
from inventory.models import InventoryLog, Ingredient

class Command(BaseCommand):
    help = '매일 사용된 식재료 재고를 일괄 차감합니다. (기본: 오늘 날짜)'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='특정 날짜 수동 처리 (YYYY-MM-DD)')

    @transaction.atomic
    def handle(self, *args, **options):
        date_str = options.get('date')
        if date_str:
            target_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
            
        plans = DietPlan.objects.filter(target_date=target_date, is_served=False)
        if not plans.exists():
            self.stdout.write(self.style.WARNING(f"{target_date}에 처리할 식단이 없거나 이미 차감 완료되었습니다."))
            return
            
        count = 0
        for plan in plans:
            if plan.headcount <= 0:
                continue
                
            for diet_menu in plan.diet_menus.all():
                for recipe in diet_menu.menu.recipes.all():
                    ing = recipe.ingredient
                    used_qty = recipe.required_amount * plan.headcount
                    
                    ing.current_stock -= used_qty
                    ing.save()
                    
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type=InventoryLog.LogType.OUT,
                        quantity=used_qty,
                        description=f"{target_date} {plan.meal_type} 일괄 차감 ({plan.headcount}명)"
                    )
            plan.is_served = True
            plan.save()
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f"{target_date} 기준 총 {count}개 식단의 재고 차감이 완료되었습니다."))
