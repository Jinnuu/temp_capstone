from forecasting.models import AttendancePrediction
from meals.models import DietPlan, DietMenu, Recipe
from django.db.models import Sum

def get_ingredient_requirements(date, meal_type):

    
    meal_map = {'breakfast': '조식', 'lunch': '중식', 'dinner': '석식'}
    target_meal_type = meal_type.lower()
    ko_meal_type = meal_map.get(target_meal_type, target_meal_type)

    prediction = AttendancePrediction.objects.filter(
        prediction_date=date, 
        meal_type=target_meal_type
    ).first()
    
    if not prediction:
        return {"error": f"{date} {target_meal_type}의 예측 데이터가 없습니다."}


    diet_plan = DietPlan.objects.filter(
        target_date=date, 
        meal_type=ko_meal_type
    ).first()
    
    if not diet_plan:
        return {"error": f"{date} {ko_meal_type}에 해당하는 식단이 DB에 없습니다."}

    ingredient_totals = {}
    has_shortage = False

    diet_menus = DietMenu.objects.filter(diet_plan=diet_plan).select_related('menu')
    
    for dm in diet_menus:
        menu_name = dm.menu.name 
        recipes = Recipe.objects.filter(menu=dm.menu).select_related('ingredient')
        
        for r in recipes:
            ingre = r.ingredient
            name = ingre.name
            
            try:
                needed_qty = prediction.predicted_count * float(r.required_amount)
            except (ValueError, TypeError):
                needed_qty = 0
            
            if name not in ingredient_totals:
                ingredient_totals[name] = {
                    'needed_amount': 0,
                    'current_stock': float(ingre.current_stock) if hasattr(ingre, 'current_stock') else 0,
                    'safe_level': float(ingre.safe_stock_level) if hasattr(ingre, 'safe_stock_level') else 0,
                    'unit': ingre.unit,
                    'included_menus': set() 
                }
            
            ingredient_totals[name]['needed_amount'] += needed_qty
            ingredient_totals[name]['included_menus'].add(menu_name) 

    for name, data in ingredient_totals.items():
        shortage = (data['needed_amount'] + data['safe_level']) - data['current_stock']
        data['order_amount'] = max(0, round(shortage, 2))
        
        if data['order_amount'] > 0:
            has_shortage = True
        

        data['included_menus'] = list(data['included_menus'])

    return {
        'items': ingredient_totals,
        'has_shortage': has_shortage,
        'prediction_count': prediction.predicted_count
    }