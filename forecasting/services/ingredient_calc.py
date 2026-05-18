from datetime import datetime
from django.db.models import Sum
from django.apps import apps

def get_current_stock(ingredient_obj, inventory_log_model):
    """실시간 입출고 로그 합산 계산"""
    in_sum = inventory_log_model.objects.filter(
        ingredient=ingredient_obj, 
        log_type__in=['IN', '입고', '1'] 
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    out_sum = inventory_log_model.objects.filter(
        ingredient=ingredient_obj, 
        log_type__in=['OUT', '출고', '2']
    ).aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    return float(in_sum) - float(out_sum)

def get_ingredient_requirements(target_date, meal_type):
    # 1. 모델 로드
    DietPlan = apps.get_model('meals', 'DietPlan')
    InventoryLog = apps.get_model('inventory', 'InventoryLog')
    Ingredient = apps.get_model('inventory', 'Ingredient')
    AttendancePrediction = apps.get_model('forecasting', 'AttendancePrediction')

    results = {
        'prediction_count': 0,
        'items': {},
        'has_shortage': False,
        'error': None
    }

    try:
        # 2. 예측 데이터 확인
        prediction = AttendancePrediction.objects.filter(
            prediction_date=target_date,
            meal_type=meal_type
        ).first()

        if not prediction:
            results['error'] = f"{target_date} {meal_type} 예측 데이터가 없습니다."
            return results

        prediction_count = prediction.predicted_count
        results['prediction_count'] = prediction_count

        # 3. 식단 확인
        meal_map = {'breakfast': '조식', 'lunch': '중식', 'dinner': '석식'}
        plan = DietPlan.objects.filter(
            target_date=target_date,
            meal_type=meal_map.get(meal_type)
        ).first()

        if not plan:
            results['error'] = f"{target_date} 식단이 없습니다."
            return results

        # 4. 루프 순회하며 재료 정보 수집
        for diet_menu in plan.diet_menus.all():
            for recipe in diet_menu.menu.recipes.all():
                ing = recipe.ingredient 
                name = ing.name
                
                # 🔥 필드명 수정: safe_stock_level
                # DB 값이 Null일 경우를 대비해 0.0으로 처리
                safe_stock = float(ing.safe_stock_level) if hasattr(ing, 'safe_stock_level') and ing.safe_stock_level is not None else 0.0
                
                current_stock = get_current_stock(ing, InventoryLog)
                needed_amount = float(recipe.required_amount) * prediction_count
                unit = getattr(ing, 'unit', 'kg')

                if name not in results['items']:
                    results['items'][name] = {
                        'needed_amount': 0,
                        'current_stock': current_stock,
                        'safe_level': safe_stock, # 템플릿에서 쓰는 키값은 유지
                        'unit': unit,
                        'included_menus': set()
                    }
                
                results['items'][name]['needed_amount'] += needed_amount
                results['items'][name]['included_menus'].add(diet_menu.menu.name)

        # 5. 부족분 계산
        for name, data in results['items'].items():
            # 부족분 = (필요량 + 안전재고) - 현재고
            order_qty = (data['needed_amount'] + data['safe_level']) - data['current_stock']
            data['order_amount'] = round(max(0, order_qty), 1)
            data['included_menus'] = list(data['included_menus'])
            
            if data['order_amount'] > 0:
                results['has_shortage'] = True

    except Exception as e:
        results['error'] = f"산출 오류: {str(e)}"

    return results

from django.db.models import Case, When, Value, IntegerField

def get_all_day_requirements(target_date):
    DietPlan = apps.get_model('meals', 'DietPlan')
    InventoryLog = apps.get_model('inventory', 'InventoryLog')
    AttendancePrediction = apps.get_model('forecasting', 'AttendancePrediction')

    results = {
        'items': {},        # 발주용 통합 데이터
        'meal_details': [], # 화면 표시용 끼니별 상세 데이터
        'has_shortage': False,
    }

    # 🔥 조식, 중식, 석식 순서 강제 지정
    plans = DietPlan.objects.filter(target_date=target_date).annotate(
        meal_order=Case(
            When(meal_type='조식', then=Value(1)),
            When(meal_type='중식', then=Value(2)),
            When(meal_type='석식', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('meal_order')
    
    for plan in plans:
        meal_map_inv = {'조식': 'breakfast', '중식': 'lunch', '석식': 'dinner'}
        prediction = AttendancePrediction.objects.filter(
            prediction_date=target_date, 
            meal_type=meal_map_inv.get(plan.meal_type)
        ).first()
        
        pred_count = prediction.predicted_count if prediction else 0
        
        meal_info = {
            'meal_type': plan.meal_type,
            'pred_count': pred_count,
            'ingredients': []
        }

        for diet_menu in plan.diet_menus.all():
            for recipe in diet_menu.menu.recipes.all():
                ing = recipe.ingredient
                needed = float(recipe.required_amount) * pred_count
                
                meal_info['ingredients'].append({
                    'name': ing.name,
                    'needed': needed,
                    'unit': ing.unit
                })

                if ing.name not in results['items']:
                    results['items'][ing.name] = {
                        'total_needed': 0,
                        'current_stock': get_current_stock(ing, InventoryLog),
                        'safe_level': float(ing.safe_stock_level or 0),
                        'unit': ing.unit
                    }
                results['items'][ing.name]['total_needed'] += needed

        results['meal_details'].append(meal_info)

    for name, data in results['items'].items():
        shortage = (data['total_needed'] + data['safe_level']) - data['current_stock']
        data['order_amount'] = round(max(0, shortage), 1)
        if data['order_amount'] > 0:
            results['has_shortage'] = True

    return results