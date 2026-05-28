import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from procurement.models import PurchaseOrder, OrderItem
from inventory.models import Ingredient

class Command(BaseCommand):
    help = "Seed procurement data for testing (including meal-based and simple orders)"

    def handle(self, *args, **options):
        User = get_user_model()
        
        # 1. Ensure suppliers exist
        suppliers = []
        for i in range(1, 4):
            username = f"supplier_{i}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"name": f"공급처 {i}"}
            )
            if created:
                user.set_password("password123")
                user.save()
            suppliers.append(user)
        
        self.stdout.write(self.style.SUCCESS(f"Found/Created {len(suppliers)} suppliers."))

        # 2. Ensure ingredients exist linked to suppliers
        categories = ["채소류", "육류", "수산물", "가공식품", "양념류"]
        ingredients = []
        for i in range(1, 11):
            ing_name = f"테스트 식재료 {i}"
            supplier = random.choice(suppliers)
            ing, created = Ingredient.objects.get_or_create(
                name=ing_name,
                defaults={
                    "category": random.choice(categories),
                    "unit": "kg",
                    "unit_price": random.randint(1000, 20000),
                    "supplier": supplier,
                    "spec": "보통",
                    "safe_stock_level": random.randint(5, 50)
                }
            )
            ingredients.append(ing)

        self.stdout.write(self.style.SUCCESS(f"Found/Created {len(ingredients)} ingredients."))

        # 3. Create Orders for the last 30 days
        start_date = date.today() - timedelta(days=30)
        
        order_count = 0
        for i in range(30):
            current_date = start_date + timedelta(days=i)
            
            # Create 1-2 orders per day
            for _ in range(random.randint(1, 2)):
                supplier = random.choice(suppliers)
                po = PurchaseOrder.objects.create(
                    supplier=supplier,
                    status=PurchaseOrder.Status.APPROVED,
                )
                
                # Add 3-5 items per order
                selected_ingredients = random.sample(ingredients, random.randint(3, 5))
                total_amount = 0
                
                for ing in selected_ingredients:
                    qty = random.randint(1, 10)
                    price = ing.unit_price * qty
                    total_amount += price
                    
                    # Randomly decide if it has target_date (Meal-based vs Simple)
                    # 50% chance for target_date to simulate the bug scenario and fix
                    has_target_date = random.choice([True, False])
                    target_dt = current_date if has_target_date else None
                    
                    OrderItem.objects.create(
                        purchase_order=po,
                        ingredient=ing,
                        target_date=target_dt,
                        required_qty=qty,
                        missing_qty=qty,
                        order_unit_price=ing.unit_price,
                        estimated_price=price
                    )
                
                po.total_amount = total_amount
                po.save()
                order_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {order_count} purchase orders."))
