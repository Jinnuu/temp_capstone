from forecasting.models import AttendancePrediction
from meals.models import DietPlan, DietMenu, Recipe
from django.db.models import Sum

def get_ingredient_requirements(date, meal_type):
    meal_map = {
        'breakfast': '조식',
        'lunch': '중식',
        'dinner': '석식'
    }
    
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


    diet_menus = DietMenu.objects.filter(diet_plan=diet_plan).select_related('menu')
    
    for dm in diet_menus:

        recipes = Recipe.objects.filter(menu=dm.menu).select_related('ingredient')
        for r in recipes:
            name = r.ingredient.name
            unit = r.ingredient.unit
            

            try:
                total_qty = prediction.predicted_count * float(r.required_amount)
            except (ValueError, TypeError):
                total_qty = 0
            
            if name in ingredient_totals:
                ingredient_totals[name]['amount'] += total_qty
            else:
                ingredient_totals[name] = {
                    'amount': total_qty, 
                    'unit': unit
                }

    return ingredient_totals