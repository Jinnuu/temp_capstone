"""Live cooking sheets: no procurement issuance or inventory mutation."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from inventory.models import SupplySpecification
from procurement.workflow import convert, quantity


def display_quantity(value):
    if value is None:
        return '계산 불가'
    number = Decimal(str(value))
    text = format(number, '.6f').rstrip('0').rstrip('.')
    return ('≈' if Decimal(text or '0') != number else '') + (text or '0')


def cooking_sheet(plan, line_notes=None):
    line_notes = line_notes or {}
    warnings, rows = [], []
    confirmed = plan.is_confirmed and plan.final_headcount is not None
    if not confirmed:
        warnings.append('최종 식수가 미확정입니다. 총량을 계산하지 않았습니다.')
    menus = list(plan.diet_menus.select_related('menu').order_by('menu__name', 'pk'))
    if not menus:
        warnings.append('식단에 메뉴가 없습니다.')
    for entry in menus:
        menu = entry.menu
        recipes = list(menu.recipes.select_related('ingredient__supplier').order_by('ingredient__name', 'pk'))
        if not recipes:
            warnings.append(f'{menu.name}: 레시피가 없습니다.')
            rows.append({'menu': menu.name, 'ingredient': '레시피 누락', 'notes': menu.cooking_notes})
        for recipe in recipes:
            ing = recipe.ingredient
            row = dict(recipe_id=recipe.pk, menu=menu.name, ingredient=ing.name, per_person=recipe.required_amount,
                       recipe_unit=recipe.unit or ing.unit, unit=ing.unit,
                       total=None, package=None, package_unit='', specification='', supplier='',
                       notes=menu.cooking_notes, remark=line_notes.get(str(recipe.pk), ''))
            try:
                amount = quantity(recipe.required_amount, '1인분 기준량', positive=True)
                # Validate compatibility even before headcount confirmation.
                base = convert(amount, row['recipe_unit'], ing.unit)
                if confirmed:
                    row['total'] = base * quantity(plan.final_headcount, '최종 식수')
                if not ing.supplier_id:
                    raise ValidationError('공급업체가 없습니다.')
                spec = SupplySpecification.objects.filter(ingredient=ing, supplier_id=ing.supplier_id).first()
                if spec is None:
                    raise ValidationError('명시적 납품규격이 없습니다.')
                size = convert(quantity(spec.base_quantity, '포장 내용량', positive=True), spec.base_unit, ing.unit)
                row.update(specification=spec.label, supplier=ing.supplier.name,
                           package_unit=spec.order_unit)
                if not spec.order_unit.strip():
                    raise ValidationError('포장 단위가 없습니다.')
                if row['total'] is not None:
                    row['package'] = row['total'] / size
            except ValidationError as exc:
                warnings.append(f'{menu.name} / {ing.name}: {"; ".join(exc.messages)}')
            row.update(total_display=display_quantity(row['total']),
                       package_display=display_quantity(row['package']),
                       per_person_display=display_quantity(row['per_person']))
            rows.append(row)
    return {'plan': plan, 'rows': rows, 'warnings': warnings,
            'confirmed': confirmed, 'headcount': plan.final_headcount if confirmed else None}
