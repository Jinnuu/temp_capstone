from django.core.management.base import BaseCommand
from meals.models import Menu, Recipe
from django.db.models import Q
import re

class Command(BaseCommand):
    help = 'Smartly auto-categorize menus based on recipes and keywords'

    def handle(self, *args, **options):
        # 1. Basic Keyword Rules (High Priority)
        basic_rules = [
            ('밥', r'.*(밥|죽|필라프|리조또|덮밥|볶음밥|비빔밥|오므라이스)$'),
            ('국', r'.*(국|찌개|탕|전골|스프|수프|육개장|해장국)$'),
            ('김치', r'.*(김치|깍두기|석박지|무생채|겉절이|동치미|나박김치|절임)$'),
            ('간식', r'.*(우유|요구르트|주스|쥬스|요플레|두유|과일|바나나|사과|떡|빵|케익|도넛|쿠키|씨리얼|시리얼)$'),
        ]

        # 2. Main/Sub Side Fallback Keywords (Low Priority)
        # Main: Must imply a substantial dish
        main_keywords = r'.*(불고기|제육|갈비|가스|까스|탕수|강정|스테이크|정식|닭|오리|훈제|삼겹살|보쌈|돈육|돈까스|치킨)$'
        # Sub: Typical accompaniments
        sub_keywords = r'.*(무침|나물|샐러드|생채|숙채|초무침|냉채|전|조림|장아찌|어묵|소시지|햄|맛살|채볶음|순두부|계란찜)$'
        
        # Ambiguous: 볶음, 튀김, 구이, 찜 -> Check for protein keywords in name
        protein_indicators = r'.*(고기|육|닭|오리|소|돼지|돈|우|해물|오징어|쭈꾸미|낙지|새우|명태|동태|가자미|고등어|자반|멸치)$'

        menus = Menu.objects.all().prefetch_related('recipes__ingredient')
        total = menus.count()
        updated = 0

        self.stdout.write(f"Starting smart auto-categorization for {total} menus...")

        for menu in menus:
            original_cat = menu.category
            new_cat = '기타'
            matched = False

            # Step 1: Check Basic Categories (Rice, Soup, etc.)
            for cat, pattern in basic_rules:
                if re.search(pattern, menu.name):
                    new_cat = cat
                    matched = True
                    break
            
            if matched:
                if original_cat != new_cat:
                    menu.category = new_cat
                    menu.save()
                    updated += 1
                continue

            # Step 2: Recipe-Aware Analysis (High Confidence)
            recipes = menu.recipes.all()
            if recipes.exists():
                protein_ing = recipes.filter(
                    Q(ingredient__category='육류') | 
                    Q(ingredient__category='계육 및 계란') | 
                    Q(ingredient__category='수산물')
                )
                if protein_ing.exists():
                    new_cat = '주반찬'
                else:
                    new_cat = '부반찬'
                matched = True
            
            # Step 3: Keyword Fallback for sides
            if not matched:
                if re.search(main_keywords, menu.name):
                    new_cat = '주반찬'
                elif re.search(sub_keywords, menu.name):
                    new_cat = '부반찬'
                elif re.search(r'.*(볶음|튀김|구이|찜)$', menu.name):
                    # If it ends in 볶음/튀김/구이/찜, check if it has protein indicators
                    if re.search(protein_indicators, menu.name):
                        new_cat = '주반찬'
                    else:
                        new_cat = '부반찬'
                else:
                    new_cat = '부반찬' # Default to sub side for unknown sides

            if original_cat != new_cat:
                menu.category = new_cat
                menu.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Finished! Updated {updated} menus using smart logic."))
