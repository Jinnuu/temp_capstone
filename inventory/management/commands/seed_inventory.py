import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from inventory.models import Ingredient, InventoryLog

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the inventory with dummy ingredients and logs for the past month."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting inventory seeding..."))

        # 1. Create or Get Dummy Ingredients
        ingredient_names = [
            ("쌀", "20kg/포", "곡류"),
            ("배추김치", "10kg", "김치류"),
            ("돼지고기(뒷다리)", "kg", "육류"),
            ("닭고기(정육)", "kg", "육류"),
            ("양파", "10kg/망", "채소류"),
            ("대파", "kg", "채소류"),
            ("식용유", "18L", "가공식품"),
            ("고추장", "14kg", "가공식품"),
        ]

        ingredients = []
        supplier = User.objects.first() # Ensure at least one user exists

        for name, spec, cat in ingredient_names:
            ing, created = Ingredient.objects.get_or_create(
                name=name,
                defaults={
                    'spec': spec,
                    'category': cat,
                    'unit': 'kg' if 'kg' in spec.lower() else 'EA',
                    'unit_price': random.randint(5000, 50000),
                    'safe_stock_level': random.randint(10, 50),
                    'supplier': supplier
                }
            )
            ingredients.append(ing)
            if created:
                self.stdout.write(f"Created ingredient: {name}")

        # 2. Generate Logs for the past month (May 1st to May 27th)
        start_date = datetime(2026, 5, 1)
        end_date = datetime(2026, 5, 27)
        delta = end_date - start_date

        total_logs = 0
        for i in range(delta.days + 1):
            current_date = start_date + timedelta(days=i)
            # TZ aware
            current_dt = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))

            for ing in ingredients:
                # Randomly choose if we have IN or OUT logs today
                # 70% chance of OUT, 40% chance of IN (to keep stock moving)
                
                # 입고 (IN) - weekly or random
                if random.random() < 0.3:
                    qty = random.randint(10, 100)
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type='입고',
                        quantity=qty,
                        transaction_date=current_dt,
                        description="정기 입고"
                    )
                    total_logs += 1

                # 출고 (OUT) - daily random
                if random.random() < 0.6:
                    qty = random.randint(1, 10)
                    InventoryLog.objects.create(
                        ingredient=ing,
                        log_type='출고',
                        quantity=qty,
                        transaction_date=current_dt,
                        description="일일 식단 사용"
                    )
                    total_logs += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_logs} logs for {len(ingredients)} ingredients."))
