"""Repeated delivery rounds in inventory base units, without rewriting legacy receipts.

Order row is the serialization mutex for scheduling and inspection. Supplier
membership uses the same policy lock as existing portal ownership changes.
Overdelivery, post-inspection edits and reopening historic closed orders require
an explicit separate policy; this service never silently authorizes them.
"""
import uuid
from datetime import date
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum, Max
from django.utils import timezone
from accounts.rbac import can
from accounts.access_service import policy_lock
from accounts.models import User
from inventory.models import Ingredient, InventoryLog
from inventory.lot_services import register_lot
from .models import PurchaseOrder, GoodsInspection, DeliveryBatch, DeliveryBatchLine, DeliveryReceipt
from .portal_services import verified_membership
from .workflow import quantity


def amount(value, *, positive=False):
    value = quantity(value, positive=positive)
    if value.as_tuple().exponent < -6:
        raise ValidationError('수량은 소수 여섯째 자리까지 입력하세요.')
    return value


def day(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ValidationError('올바른 날짜를 입력하세요.')


def progress(item):
    old = GoodsInspection.objects.filter(order_item=item).first()
    legacy_accepted = old.accepted_qty if old else Decimal('0')
    rows = DeliveryReceipt.objects.filter(line__order_item=item)
    accepted = legacy_accepted + (rows.aggregate(q=Sum('accepted_quantity'))['q'] or Decimal('0'))
    delivered = (old.delivered_qty if old else Decimal('0')) + (rows.aggregate(q=Sum('delivered_quantity'))['q'] or Decimal('0'))
    reserved = DeliveryBatchLine.objects.filter(order_item=item, receipt__isnull=True).aggregate(q=Sum('planned_quantity'))['q'] or Decimal('0')
    return dict(accepted=accepted, delivered=delivered, rejected=delivered-accepted,
                remaining=max(Decimal('0'), item.required_qty-accepted), reserved=reserved,
                available=max(Decimal('0'), item.required_qty-accepted-reserved))


def _open(order):
    if order.status not in ('대기', '승인') or order.needs_review:
        raise ValidationError('완료·재검토 발주는 새 납품을 처리할 수 없습니다. 담당자 검토가 필요합니다.')


@transaction.atomic
def schedule(actor, order_id, *, request_key, expected_date, quantities, contact, notes=''):
    policy_lock()
    actor = User.objects.select_for_update().get(pk=actor.pk)
    if not can(actor, 'portal.write'):
        raise PermissionDenied
    member = verified_membership(actor, lock=True)
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id, supplier_id=member.supplier.user_id)
    key = uuid.UUID(str(request_key))
    expected = day(expected_date)
    if not isinstance(quantities, dict) or not quantities:
        raise ValidationError('납품할 품목과 수량을 입력하세요.')
    items = {str(i.pk): i for i in order.items.select_related('ingredient')}
    if set(quantities)-items.keys():
        raise ValidationError('다른 발주의 품목을 입력할 수 없습니다.')
    values = {str(k): amount(v, positive=True) for k, v in quantities.items()}
    if not contact.strip() or len(contact)>100 or len(notes)>1000:
        raise ValidationError('납품 담당자와 비고 길이를 확인하세요.')
    existing = DeliveryBatch.objects.filter(request_key=key).first()
    if existing:
        previous = {str(x.order_item_id): x.planned_quantity for x in existing.lines.all()}
        if (existing.order_id, existing.created_by_id, existing.expected_date, existing.contact, existing.notes, previous) != (order.pk, actor.pk, expected, contact.strip(), notes.strip(), values):
            raise ValidationError('이미 다른 요청에 사용한 요청 키입니다.')
        return existing
    _open(order)
    if expected < timezone.localdate():
        raise ValidationError('납품 예정일은 오늘 이후여야 합니다.')
    fulfillment = getattr(order, 'fulfillment', None)
    if not fulfillment or fulfillment.state not in ('ACCEPTED', 'PREPARING', 'DISPATCHED'):
        raise ValidationError('발주를 먼저 수락한 후 납품 회차를 등록하세요.')
    for key_id, value in values.items():
        item = items[key_id]
        if GoodsInspection.objects.filter(order_item=item).exists():
            raise ValidationError('기존 단건 검수 품목은 재개 정책 확인 후 처리하세요.')
        if value > progress(item)['available']:
            raise ValidationError('합격량과 미검수 예정량을 제외한 잔량을 초과합니다. 초과 납품은 별도 승인 정책이 필요합니다.')
    sequence = (order.delivery_batches.aggregate(n=Max('sequence'))['n'] or 0)+1
    batch = DeliveryBatch.objects.create(order=order, sequence=sequence, request_key=key, expected_date=expected, contact=contact.strip(), notes=notes.strip(), created_by=actor)
    for key_id, value in values.items():
        item = items[key_id]
        DeliveryBatchLine.objects.create(batch=batch, order_item=item, planned_quantity=value, base_unit=item.ingredient.unit, specification=item.purchase_spec or '')
    return batch


@transaction.atomic
def inspect(actor, line_id, *, delivered, accepted, actual_date, specification, notes='', expiration=None):
    policy_lock()
    actor = User.objects.select_for_update().get(pk=actor.pk)
    # Supplier+SUB remains unable to approve its own delivery or change stock.
    if not can(actor, 'inspection.write') or actor.role == 'SUPPLIER':
        raise PermissionDenied
    # Read only identifier before locking; every writer locks order BEFORE item.
    order_id = DeliveryBatchLine.objects.values_list('batch__order_id', flat=True).get(pk=line_id)
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id)
    line = DeliveryBatchLine.objects.select_related('order_item__ingredient', 'batch').get(pk=line_id)
    item = order.items.select_for_update().select_related('ingredient').get(pk=line.order_item_id)
    delivered, accepted = amount(delivered), amount(accepted)
    actual = day(actual_date)
    expiration = day(expiration) if expiration else None
    if actual > timezone.localdate() or actual < timezone.localtime(line.batch.created_at).date():
        raise ValidationError('실제 납품일은 회차 등록일부터 오늘 사이여야 합니다.')
    if accepted > delivered or delivered > line.planned_quantity:
        raise ValidationError('합격량 ≤ 실납량 ≤ 회차 예정량이어야 합니다. 초과량은 별도 승인 정책이 필요합니다.')
    if not specification.strip() or len(specification)>200 or len(notes)>1000:
        raise ValidationError('규격과 비고 길이를 확인하세요.')
    if (delivered != line.planned_quantity or accepted != delivered) and not notes.strip():
        raise ValidationError('수량 차이 또는 불합격 사유를 입력하세요.')
    if expiration and expiration < timezone.localdate() and accepted:
        raise ValidationError('유통기한이 지난 물품은 합격 입고할 수 없습니다.')
    values = (actual, delivered, accepted, specification.strip(), notes.strip(), expiration)
    previous = DeliveryReceipt.objects.filter(line=line).first()
    if previous:
        if (previous.actual_date, previous.delivered_quantity, previous.accepted_quantity, previous.specification, previous.notes, previous.expiration_date) != values:
            raise ValidationError('이미 검수한 회차입니다. 원본을 덮어쓰지 않습니다. 정정 절차가 필요합니다.')
        return previous
    _open(order)
    if GoodsInspection.objects.filter(order_item=item).exists():
        raise ValidationError('기존 단건 검수와 회차별 검수를 중복 처리할 수 없습니다.')
    if line.base_unit != item.ingredient.unit:
        raise ValidationError('재고 단위가 변경됐습니다. 담당자 확인이 필요합니다.')
    if progress(item)['accepted'] + accepted > item.required_qty:
        raise ValidationError('발주 합격 잔량을 초과합니다.')
    Ingredient.objects.select_for_update().get(pk=item.ingredient_id)
    log = None
    if accepted:
        log = InventoryLog.objects.create(ingredient=item.ingredient, log_type='입고', quantity=accepted,
            expiration_date=expiration, description=f'발주 #{order.pk} 납품 {line.batch.sequence}회차 합격 입고')
        register_lot(log)
    receipt = DeliveryReceipt.objects.create(line=line, actual_date=actual, delivered_quantity=delivered,
        accepted_quantity=accepted, specification=specification.strip(), notes=notes.strip(),
        expiration_date=expiration, inspected_by=actor, inventory_log=log)
    if all(progress(i)['remaining'] == 0 for i in order.items.all()):
        order.status = '완료'
        order.save(update_fields=['status'])
    return receipt
