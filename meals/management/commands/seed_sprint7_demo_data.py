
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from forecasting.models import AttendancePrediction
from inventory.models import Ingredient, InventoryLog
from meals.models import DietMenu, DietPlan, Menu, Recipe


class Command(BaseCommand):
    help = "Create Sprint7 demo ingredients, menus, recipes, meal plans and predictions."

    def handle(self, *args, **options):
        ingredients = [
            ("쌀", "곡류", "kg", 3200, 50, Decimal("120")),
            ("양파", "채소/농가공품", "kg", 2300, 10, Decimal("4")),
            ("돼지고기", "축산/축산가공품", "kg", 10700, 10, Decimal("5")),
            ("건미역", "수산/수산가공품", "kg", 18500, 3, Decimal("8")),
            ("배추김치", "김치/절임류", "kg", 5400, 15, Decimal("30")),
            ("카레분말", "가공식품", "kg", 6400, 5, Decimal("6")),
            ("감자", "채소/농가공품", "kg", 1800, 10, Decimal("25")),
            ("대파", "채소/농가공품", "kg", 2600, 5, Decimal("3")),
            ("달걀", "축산/축산가공품", "판", 7500, 3, Decimal("12")),
            ("두부", "가공식품", "모", 1200, 10, Decimal("20")),
        ]
        ing = {}
        for name, category, unit, price, safe, stock in ingredients:
            obj, _ = Ingredient.objects.update_or_create(
                name=name,
                defaults={"category": category, "unit": unit, "unit_price": price, "safe_stock_level": safe, "spec": "test demo", "description": "Sprint7 발표용 테스트 데이터"},
            )
            ing[name] = obj
            if not InventoryLog.objects.filter(ingredient=obj, description="Sprint7 demo initial stock").exists():
                InventoryLog.objects.create(ingredient=obj, log_type="입고", quantity=stock, description="Sprint7 demo initial stock")

        recipes = {
            "쌀밥": ("밥", [("쌀", "0.15")]),
            "잡곡밥": ("밥", [("쌀", "0.13")]),
            "제육볶음": ("주반찬", [("돼지고기", "0.12"), ("양파", "0.03"), ("대파", "0.01")]),
            "미역국": ("국", [("건미역", "0.01"), ("대파", "0.005")]),
            "카레라이스": ("주반찬", [("쌀", "0.15"), ("카레분말", "0.02"), ("감자", "0.05"), ("양파", "0.03")]),
            "배추김치": ("김치", [("배추김치", "0.04")]),
            "계란국": ("국", [("달걀", "0.02"), ("대파", "0.004")]),
            "두부조림": ("부반찬", [("두부", "0.10"), ("대파", "0.004")]),
        }
        menus = {}
        for menu_name, (cat, items) in recipes.items():
            menu, _ = Menu.objects.update_or_create(name=menu_name, defaults={"category": cat})
            menus[menu_name] = menu
            for ing_name, amount in items:
                Recipe.objects.update_or_create(menu=menu, ingredient=ing[ing_name], defaults={"required_amount": Decimal(amount)})

        start = date.today()
        for offset in range(7):
            d = start + timedelta(days=offset)
            day_sets = {
                "조식": ["쌀밥", "계란국", "배추김치"],
                "중식": ["잡곡밥", "제육볶음", "미역국", "배추김치"],
                "석식": ["카레라이스", "두부조림", "배추김치"],
            }
            headcounts = {"조식": 80 + offset, "중식": 120 + offset, "석식": 70 + offset}
            for meal_type, menu_names in day_sets.items():
                plan, _ = DietPlan.objects.update_or_create(target_date=d, meal_type=meal_type, defaults={"headcount": headcounts[meal_type]})
                DietMenu.objects.filter(diet_plan=plan).delete()
                for name in menu_names:
                    DietMenu.objects.create(diet_plan=plan, menu=menus[name])

        meal_type_values = {"조식": "breakfast", "중식": "lunch", "석식": "dinner"}
        for label, value in meal_type_values.items():
            AttendancePrediction.objects.get_or_create(
                prediction_date=start,
                meal_type=value,
                defaults={"predicted_count": {"조식": 82, "중식": 238, "석식": 96}[label], "model_name": "Sprint7 Demo", "input_features": {"seed": True}},
            )
        self.stdout.write(self.style.SUCCESS("Sprint7 demo data created/updated."))
