"""Confirmed headcounts, explicit units, order snapshots and inspected receipts."""
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from inventory.models import Ingredient, InventoryLog, SupplySpecification
from meals.models import DietPlan, Recipe
from .models import (GoodsInspection, InventoryTransactionKey, OrderItem, PurchaseOrder,
                     ProcurementPlan, ProcurementPlanLine)

MEALS = ['조식', '중식', '석식']
UNIT_MAP = {'kg': ('mass', Decimal('1')), 'g': ('mass', Decimal('.001')),
            'l': ('volume', Decimal('1')), 'ml': ('volume', Decimal('.001')),
            'ea': ('count', Decimal('1')), '개': ('count', Decimal('1'))}


def quantity(value, label='수량', *, positive=False):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal('999999999') or (positive and number == 0):
            raise ValueError()
        return number
    except (ValueError, InvalidOperation, TypeError):
        raise ValidationError(f'{label}: 유한한 {"양수" if positive else "0 이상"} 수량을 입력하세요.')


def convert(value, source, target):
    value = quantity(value)
    source, target = source.strip().lower(), target.strip().lower()
    if not source or not target:
        raise ValidationError('기준 단위를 등록하세요.')
    if source == target:
        return value
    a, b = UNIT_MAP.get(source), UNIT_MAP.get(target)
    if not a or not b or a[0] != b[0]:
        raise ValidationError(f'단위 환산 불가: {source} → {target}. 명시적 납품규격을 확인하세요.')
    return value * a[1] / b[1]


def current_stock(ingredient):
    totals = {r['log_type']: r['total'] for r in InventoryLog.objects.filter(ingredient=ingredient).values('log_type').annotate(total=Sum('quantity'))}
    return sum((totals.get(kind, Decimal('0')) * sign for kind, sign in [('입고',1),('출고',-1),('폐기',-1),('조정',1)]), Decimal('0'))


def invalidate_plans(meal_ids=None):
    plans = ProcurementPlan.objects.all()
    for plan in plans.only('id', 'meal_ids'):
        if meal_ids is None or set(plan.meal_ids).intersection(meal_ids):
            ProcurementPlan.objects.filter(pk=plan.pk).update(needs_review=True)
            PurchaseOrder.objects.filter(workflow_plan=plan).exclude(status='완료').update(needs_review=True)


def fingerprint(meal_ids):
    data=[]
    for plan in DietPlan.objects.filter(pk__in=meal_ids).order_by('id'):
        data.append([plan.pk,str(plan.target_date),plan.meal_type,plan.final_headcount,plan.is_confirmed,
                     list(plan.diet_menus.order_by('id').values_list('menu_id',flat=True))])
        for dm in plan.diet_menus.order_by('id'):
            for recipe in dm.menu.recipes.select_related('ingredient').order_by('id'):
                ing=recipe.ingredient
                specs=list(ing.supply_specs.order_by('id').values('supplier_id','base_quantity','base_unit','order_unit','unit_price','label','order_increment'))
                data.append([recipe.pk,str(recipe.required_amount),recipe.unit,ing.pk,ing.unit,ing.supplier_id,str(ing.safe_stock_level),specs])
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,default=str,sort_keys=True).encode()).hexdigest()


@transaction.atomic
def save_headcount(plan_id, manual, final=None):
    plan=DietPlan.objects.select_for_update().get(pk=plan_id)
    manual=quantity(manual,'예상 식수')
    if manual != manual.to_integral_value():
        raise ValidationError('식수는 정수여야 합니다.')
    if plan.is_served:
        raise ValidationError('이미 사용 확정된 식단의 식수는 변경할 수 없습니다.')
    old=(plan.headcount,plan.final_headcount)
    plan.headcount=int(manual)
    if final is not None:
        count=quantity(final,'최종 식수')
        if count != count.to_integral_value():
            raise ValidationError('최종 식수는 정수여야 합니다.')
        plan.final_headcount=int(count)
        plan.headcount_confirmed_at=timezone.now()
        plan.is_confirmed=True
    elif plan.headcount != old[0]:
        plan.final_headcount=None
        plan.headcount_confirmed_at=None
        plan.is_confirmed=False
    plan.save()
    if old != (plan.headcount,plan.final_headcount):
        invalidate_plans([plan.pk])
    return plan


def build_preview(start, end, days=None):
    if end < start or (end-start).days > 62:
        raise ValidationError('조회 기간은 시작일 이후 63일 이내여야 합니다.')
    groups=[]; details=[]; meal_ids=[]; balances={}; errors=[]
    day=start
    while day<=end:
        if day.weekday()>4 or (days is not None and str(day.weekday()) not in days):
            day+=timedelta(days=1);continue
        last=day+timedelta(days=3 if day.weekday()==4 else 1)
        plans=DietPlan.objects.filter(target_date__range=(day,last)).prefetch_related('diet_menus__menu__recipes__ingredient')
        plans=[p for p in plans if (p.target_date==day and p.meal_type=='석식') or (day<p.target_date<last and p.meal_type in MEALS) or (p.target_date==last and p.meal_type in MEALS[:2])]
        plans.sort(key=lambda p:(p.target_date,MEALS.index(p.meal_type)))
        needs=defaultdict(lambda:Decimal('0')); ingredients={}
        for plan in plans:
            meal_ids.append(plan.pk)
            if plan.final_headcount is None:
                errors.append(f'{plan.target_date} {plan.meal_type}: 최종 식수를 확정하세요.');continue
            if not plan.diet_menus.exists():
                errors.append(f'{plan.target_date} {plan.meal_type}: 메뉴가 없습니다.');continue
            for dm in plan.diet_menus.all():
                recipes=list(dm.menu.recipes.all())
                if not recipes:
                    errors.append(f'{dm.menu.name}: 레시피가 없습니다.');continue
                for recipe in recipes:
                    ing=recipe.ingredient
                    try:
                        amount=convert(quantity(recipe.required_amount,positive=True),recipe.unit or ing.unit,ing.unit)*plan.final_headcount
                    except ValidationError as exc:
                        errors.append(f'{dm.menu.name}/{ing.name}: {exc.messages[0]}');continue
                    details.append({'date':str(plan.target_date),'meal':plan.meal_type,'headcount':plan.final_headcount,'menu':dm.menu.name,'ingredient':ing.name,'per_person':str(recipe.required_amount),'recipe_unit':recipe.unit or ing.unit,'needed':str(amount),'unit':ing.unit,'notes':''})
                    if amount>0:
                        needs[ing.pk]+=amount;ingredients[ing.pk]=ing
        for ing_id, needed in needs.items():
            ing=ingredients[ing_id]
            try:
                if not ing.supplier_id:
                    raise ValidationError('공급업체를 지정하세요.')
                from accounts.supplier_identity import eligible_order_accounts
                if not eligible_order_accounts().filter(pk=ing.supplier_id).exists():
                    raise ValidationError('직원 로그인 계정이 아닌 업체 발주 계정을 지정하세요.')
                spec=SupplySpecification.objects.filter(ingredient=ing,supplier_id=ing.supplier_id).first()
                if not spec:
                    raise ValidationError('납품 포장규격을 등록하세요.')
                size=convert(quantity(spec.base_quantity,positive=True),spec.base_unit,ing.unit)
                if not spec.order_unit.strip():
                    raise ValidationError('발주 단위가 없습니다.')
                from inventory.models import StockLot
                if StockLot.objects.filter(incoming_log__ingredient=ing, incoming_log__expiration_date__lt=last, remaining_quantity__gt=0).exists():
                    raise ValidationError('사용일 이전 만료 lot가 있습니다. 폐기·재고 상태를 먼저 확인하세요.')
                before=balances.setdefault(ing_id,current_stock(ing))
                if before<0:
                    raise ValidationError('음수 재고를 확인하고 조정하세요.')
                shortage=max(Decimal('0'),needed+ing.safe_stock_level-before)
                increment=quantity(spec.order_increment, '발주 간격', positive=True)
                packs=(shortage/size/increment).to_integral_value(rounding=ROUND_CEILING)*increment
                balances[ing_id]=before+packs*size-needed
                groups.append({'order_date':day,'ingredient':ing,'supplier':ing.supplier,'needed_qty':needed,'stock_before':before,'safe_stock':ing.safe_stock_level,'shortage_qty':shortage,'package_size':size,'package_quantity':packs,'order_increment':increment,'order_unit':spec.order_unit,'unit_price':spec.unit_price,'spec_snapshot':spec.label})
            except ValidationError as exc:
                errors.append(f'{ing.name}: {exc.messages[0]}')
        day+=timedelta(days=1)
    if not meal_ids:
        errors.append('선택한 발주일에 연결된 식단이 없습니다. 주말 식단은 금요일 발주에 포함됩니다.')
    return {'lines':groups,'details':details,'meal_ids':list(dict.fromkeys(meal_ids)),'errors':list(dict.fromkeys(errors))}


@transaction.atomic
def create_plan(start,end,actor,request_key,days=None):
    key=uuid.UUID(str(request_key))
    existing=ProcurementPlan.objects.filter(request_key=key).first()
    if existing:
        if existing.created_by_id!=actor.pk:
            raise ValidationError('다른 사용자의 요청 키입니다.')
        return existing
    preview=build_preview(start,end,days)
    if preview['errors']:
        raise ValidationError(preview['errors'])
    plan, created = ProcurementPlan.objects.get_or_create(request_key=key, defaults={
        'start_date':start,'end_date':end,'created_by':actor,'meal_ids':preview['meal_ids'],
        'details':preview['details'],'source_fingerprint':fingerprint(preview['meal_ids'])})
    if not created:
        if plan.created_by_id != actor.pk:
            raise ValidationError('다른 사용자의 요청 키입니다.')
        return plan
    for line in preview['lines']:
        ProcurementPlanLine.objects.create(plan=plan,**line)
    return plan


@transaction.atomic
def confirm_orders(plan_id,actor,adjustments=None):
    plan=ProcurementPlan.objects.select_for_update().get(pk=plan_id)
    from accounts.rbac import can
    if plan.created_by_id!=actor.pk and not can(actor,'accounts.manage'):
        raise ValidationError('이 발주예정서를 확정할 권한이 없습니다.')
    if plan.orders.exists():
        return list(plan.orders.all())
    if plan.needs_review or plan.source_fingerprint!=fingerprint(plan.meal_ids):
        raise ValidationError('식단·식수·레시피·규격이 변경됐습니다. 발주예정서를 다시 생성하세요.')
    orders={}
    for line in plan.lines.select_related('ingredient','supplier').order_by('order_date','supplier__name','ingredient__name'):
        packs=quantity((adjustments or {}).get(str(line.pk),line.package_quantity),'발주 포장수량')
        if packs/line.order_increment!=(packs/line.order_increment).to_integral_value() or packs<line.package_quantity:
            raise ValidationError('발주수량은 부족분 이상이며 등록된 발주 간격의 배수여야 합니다.')
        if packs==0:
            continue
        # Stock changes since preview require a fresh review, never silently use a stale snapshot.
        first_line=not plan.lines.filter(ingredient=line.ingredient,order_date__lt=line.order_date).exists()
        if first_line and current_stock(line.ingredient)!=line.stock_before:
            raise ValidationError(f'{line.ingredient.name}: 재고가 변경됐습니다. 재계산하세요.')
        key=(line.order_date,line.supplier_id)
        if key not in orders:
            orders[key]=PurchaseOrder.objects.create(supplier=line.supplier,workflow_plan=plan,confirmed_at=timezone.now(),status='승인')
        order=orders[key]
        amount=int((packs*line.unit_price).quantize(Decimal('1'),rounding=ROUND_CEILING))
        OrderItem.objects.create(purchase_order=order,ingredient=line.ingredient,target_date=line.order_date,required_qty=packs*line.package_size,missing_qty=line.shortage_qty,order_unit_price=line.ingredient.unit_price,estimated_price=amount,package_quantity=packs,order_unit=line.order_unit,spec_snapshot=line.spec_snapshot)
        order.total_amount+=amount;order.save(update_fields=['total_amount'])
    plan.status='ordered';plan.save(update_fields=['status'])
    return list(orders.values())


@transaction.atomic
def inspect_item(item_id,actor,delivered,accepted,condition,specification,notes='',expiration=None):
    from accounts.rbac import can
    if getattr(actor,'role',None)=='SUPPLIER' and not can(actor,'inspection.write'):
        raise ValidationError('공급업체 계정은 검수 합격량을 확정할 수 없습니다.')
    item=OrderItem.objects.select_for_update().select_related('purchase_order','ingredient').get(pk=item_id)
    # Matching duplicate submissions are idempotent; differing edits require a correction workflow.
    delivered=quantity(delivered,'납품량');accepted=quantity(accepted,'합격량')
    if max(delivered.as_tuple().exponent * -1,accepted.as_tuple().exponent * -1)>6:
        raise ValidationError('검수 수량은 소수 여섯째 자리까지 입력하세요.')
    if accepted>delivered or condition not in ['정상','이상','반품'] or not specification.strip():
        raise ValidationError('합격량·상태·규격을 확인하세요. 합격량은 납품량 이하여야 합니다.')
    if (delivered!=item.required_qty or accepted!=delivered or condition!='정상') and not notes.strip():
        raise ValidationError('수량 차이 또는 상태 이상의 사유를 기록하세요.')
    if condition=='반품' and accepted:
        raise ValidationError('반품 품목의 합격 입고량은 0이어야 합니다.')
    if expiration and expiration<timezone.localdate():
        raise ValidationError('유통기한이 지난 품목은 입고할 수 없습니다.')
    previous=GoodsInspection.objects.filter(order_item=item).first()
    if previous:
        if (previous.delivered_qty,previous.accepted_qty,previous.condition,previous.specification,previous.notes,previous.expiration_date)==(delivered,accepted,condition,specification,notes,expiration):
            return previous
        raise ValidationError('이미 확정된 검수입니다. 기존 이력을 덮어쓰지 않습니다.')
    if item.purchase_order.status=='완료':
        raise ValidationError('기존 완료 발주는 입고 이력 확인 후 별도로 정정하세요.')
    if item.purchase_order.needs_review:
        raise ValidationError('변경된 발주를 재검토하세요.')
    Ingredient.objects.select_for_update().get(pk=item.ingredient_id)
    log=None
    if accepted:
        log=InventoryLog.objects.create(ingredient=item.ingredient,log_type='입고',quantity=accepted,expiration_date=expiration,description=f'발주 #{item.purchase_order_id} 검수 합격 입고')
    if log is not None:
        from inventory.lot_services import register_lot
        register_lot(log)
    inspection=GoodsInspection.objects.create(order_item=item,inspected_by=actor,delivered_qty=delivered,accepted_qty=accepted,condition=condition,specification=specification,notes=notes,expiration_date=expiration,inventory_log=log)
    order=PurchaseOrder.objects.select_for_update().get(pk=item.purchase_order_id)
    if not order.items.filter(inspection__isnull=True).exists():
        order.status='완료';order.save(update_fields=['status'])
    return inspection


@transaction.atomic
def record_inventory(ingredient_id,kind,amount,actor,request_key,when,expiration=None,notes=''):
    from accounts.rbac import can
    if getattr(actor,'role',None)=='SUPPLIER' and not can(actor,'inventory.write'):
        raise ValidationError('공급업체 계정은 재고 거래를 확정할 수 없습니다.')
    key=uuid.UUID(str(request_key))
    previous=InventoryTransactionKey.objects.filter(request_key=key).select_related('inventory_log').first()
    if previous:
        log=previous.inventory_log
        if (log.ingredient_id,log.log_type,log.quantity,log.transaction_date,log.expiration_date,log.description)!=(int(ingredient_id),kind,Decimal(str(amount)),when,expiration,notes):
            raise ValidationError('이미 사용한 요청 키입니다.')
        return log
    ing=Ingredient.objects.select_for_update().get(pk=ingredient_id)
    # A concurrent request may have committed while the ingredient lock was pending.
    previous=InventoryTransactionKey.objects.filter(request_key=key).first()
    if previous:
        return record_inventory(ingredient_id,kind,amount,actor,key,when,expiration,notes)
    amount=quantity(amount,positive=True)
    if kind not in ['입고','출고','폐기','조정']:
        raise ValidationError('잘못된 거래 구분입니다.')
    if kind in ['출고','폐기'] and amount>current_stock(ing):
        raise ValidationError('현재 재고보다 많은 수량을 출고할 수 없습니다.')
    if expiration and expiration<when.date():
        raise ValidationError('거래일 이전 유통기한을 확인하세요.')
    log=InventoryLog.objects.create(ingredient=ing,log_type=kind,quantity=amount,transaction_date=when,expiration_date=expiration,description=notes)
    from inventory.lot_services import register_lot, allocate_fifo
    if kind in ['입고','조정']:
        register_lot(log)
    else:
        allocate_fifo(log)
    InventoryTransactionKey.objects.create(request_key=key,inventory_log=log)
    return log


@transaction.atomic
def create_manual_plan(ingredient_quantities,target_date,actor,request_key):
    """Manual stock replenishment shares specification, snapshot and approval rules."""
    key=uuid.UUID(str(request_key))
    existing=ProcurementPlan.objects.filter(request_key=key).first()
    if existing:
        if existing.created_by_id!=actor.pk:raise ValidationError('다른 사용자의 요청 키입니다.')
        return existing
    totals=defaultdict(lambda:Decimal('0'))
    for ingredient_id,value in ingredient_quantities:
        if not str(ingredient_id).isdigit():raise ValidationError('잘못된 식재료 ID입니다.')
        amount=quantity(value)
        if amount:totals[int(ingredient_id)]+=amount
    if not totals:raise ValidationError('발주할 품목이 없습니다.')
    lines=[];details=[]
    for ingredient_id,amount in totals.items():
        ing=Ingredient.objects.filter(pk=ingredient_id).select_related('supplier').first()
        if not ing or not ing.supplier_id:raise ValidationError('식재료와 공급업체를 지정하세요.')
        from accounts.supplier_identity import eligible_order_accounts
        if not eligible_order_accounts().filter(pk=ing.supplier_id).exists():raise ValidationError('업체 발주 계정을 지정하세요. 직원 계정으로 발주할 수 없습니다.')
        spec=SupplySpecification.objects.filter(ingredient=ing,supplier=ing.supplier).first()
        if not spec:raise ValidationError(f'{ing.name}: 납품규격을 등록하세요.')
        size=convert(quantity(spec.base_quantity,positive=True),spec.base_unit,ing.unit)
        increment=quantity(spec.order_increment, '발주 간격', positive=True)
        packs=(amount/size/increment).to_integral_value(rounding=ROUND_CEILING)*increment
        lines.append(dict(order_date=target_date,ingredient=ing,supplier=ing.supplier,needed_qty=amount,stock_before=current_stock(ing),safe_stock=ing.safe_stock_level,shortage_qty=amount,package_size=size,package_quantity=packs,order_increment=increment,order_unit=spec.order_unit,unit_price=spec.unit_price,spec_snapshot=spec.label))
        details.append(dict(date=str(target_date),meal='재고 보충',headcount='-',menu='수동 간편발주',ingredient=ing.name,per_person='-',recipe_unit=ing.unit,needed=str(amount),unit=ing.unit,notes='영양사 직접 요청량'))
    plan,created=ProcurementPlan.objects.get_or_create(request_key=key,defaults=dict(start_date=target_date,end_date=target_date,created_by=actor,details=details,source_fingerprint=fingerprint([])))
    if created:
        for line in lines:ProcurementPlanLine.objects.create(plan=plan,**line)
    elif plan.created_by_id!=actor.pk:raise ValidationError('다른 사용자의 요청 키입니다.')
    return plan
