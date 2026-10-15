"""Shared confirmed-headcount requirements for legacy forecasting screens."""
from decimal import Decimal
from django.apps import apps
from procurement.workflow import convert,current_stock
from django.core.exceptions import ValidationError


def get_current_stock(ingredient_obj, inventory_log_model=None):
    return current_stock(ingredient_obj)


def _calculate(target_date,meal_type=None):
    DietPlan=apps.get_model('meals','DietPlan')
    meal_map={'breakfast':'조식','lunch':'중식','dinner':'석식'}
    plans=DietPlan.objects.filter(target_date=target_date).prefetch_related('diet_menus__menu__recipes__ingredient')
    if meal_type:
        plans=plans.filter(meal_type=meal_map.get(meal_type,meal_type))
    result={'items':{},'meal_details':[],'has_shortage':False,'error':None,'prediction_count':0}
    errors=[]
    for plan in sorted(plans,key=lambda p:['조식','중식','석식','기타'].index(p.meal_type)):
        if plan.final_headcount is None:
            errors.append(f'{plan.target_date} {plan.meal_type}: 최종 식수를 확정하세요.');continue
        count=plan.final_headcount
        result['prediction_count']+=count
        detail={'meal_type':plan.meal_type,'pred_count':count,'ingredients':[]}
        for dm in plan.diet_menus.all():
            recipes=list(dm.menu.recipes.all())
            if not recipes:errors.append(f'{dm.menu.name}: 레시피가 없습니다.')
            for recipe in recipes:
                ing=recipe.ingredient
                try:
                    needed=convert(recipe.required_amount,recipe.unit or ing.unit,ing.unit)*count
                except ValidationError as exc:
                    errors.extend(exc.messages);continue
                item=result['items'].setdefault(ing.name,{'needed_amount':Decimal('0'),'total_needed':Decimal('0'),'current_stock':current_stock(ing),'safe_level':ing.safe_stock_level,'unit':ing.unit,'included_menus':[]})
                item['needed_amount']+=needed;item['total_needed']+=needed
                if dm.menu.name not in item['included_menus']:item['included_menus'].append(dm.menu.name)
                detail['ingredients'].append({'name':ing.name,'needed':needed,'unit':ing.unit})
        result['meal_details'].append(detail)
    if not plans:errors.append('해당 날짜의 식단이 없습니다.')
    for item in result['items'].values():
        item['order_amount']=max(Decimal('0'),item['total_needed']+item['safe_level']-item['current_stock']) if item['total_needed']>0 else Decimal('0')
        result['has_shortage']|=item['order_amount']>0
    if errors:
        result['error']=' / '.join(dict.fromkeys(errors))
    return result


def get_ingredient_requirements(target_date,meal_type):
    return _calculate(target_date,meal_type)


def get_all_day_requirements(target_date):
    return _calculate(target_date)
