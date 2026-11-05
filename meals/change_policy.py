"""Shared guards for live meal edits; no issued-document policy is inferred."""
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import DietPlan


@transaction.atomic
def guard_menu_change(menu_ids):
    plans = list(DietPlan.objects.select_for_update().filter(
        diet_menus__menu_id__in=menu_ids).order_by('pk'))
    if any(plan.is_served for plan in plans):
        raise ValidationError('사용 완료된 식단에 연결된 메뉴·레시피는 변경할 수 없습니다. 별도 메뉴로 등록하세요.')
    return {plan.pk for plan in plans}


def mark_menu_change(menu_ids):
    from procurement.workflow import invalidate_plans
    ids = set(DietPlan.objects.filter(diet_menus__menu_id__in=menu_ids).values_list('pk', flat=True))
    if ids:
        invalidate_plans(ids)


def guard_plan_delete(plans):
    """Keep rows referenced by JSON plan snapshots or cooking notes intact."""
    from procurement.models import ProcurementPlan
    ids = set(plans.values_list('pk', flat=True))
    if plans.filter(is_served=True).exists() or plans.filter(cooking_instruction__isnull=False).exists():
        raise ValidationError('사용 완료 또는 조리지시서가 연결된 식단은 삭제할 수 없습니다.')
    if any(ids.intersection(plan.meal_ids) for plan in ProcurementPlan.objects.only('meal_ids')):
        raise ValidationError('발주예정서가 연결된 식단은 삭제할 수 없습니다. 변경은 재검토 절차를 이용하세요.')
