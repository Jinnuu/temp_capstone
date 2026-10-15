"""FIFO for explicitly recorded lots; unassigned historic balances are not guessed."""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum,Q
from django.utils import timezone
from .models import StockLot,StockAllocation


def register_lot(log):
    if log.log_type in ['입고','조정'] and log.quantity>0:
        StockLot.objects.get_or_create(incoming_log=log,defaults={'remaining_quantity':log.quantity})


@transaction.atomic
def allocate_fifo(outgoing_log):
    lots=list(StockLot.objects.select_for_update().filter(incoming_log__ingredient_id=outgoing_log.ingredient_id,remaining_quantity__gt=0).select_related('incoming_log').order_by('incoming_log__transaction_date','id'))
    if outgoing_log.lot_allocations.exists():
        return
    if not lots:
        # Legacy inventory predates lot tracking: ledger deduction still works, no fabricated FIFO proof.
        return
    valid=[lot for lot in lots if lot.incoming_log.transaction_date <= outgoing_log.transaction_date and (outgoing_log.log_type=='폐기' or lot.incoming_log.expiration_date is None or lot.incoming_log.expiration_date>=timezone.localdate(outgoing_log.transaction_date))]
    remaining=abs(outgoing_log.quantity)
    if sum((lot.remaining_quantity for lot in valid),Decimal('0'))<remaining:
        raise ValidationError('유효한 lot 재고가 부족합니다. 유통기한·기존 미배정 재고를 확인하세요.')
    for lot in valid:
        take=min(remaining,lot.remaining_quantity)
        if not take:
            break
        StockAllocation.objects.create(outgoing_log=outgoing_log,lot=lot,quantity=take)
        lot.remaining_quantity-=take;lot.save(update_fields=['remaining_quantity'])
        remaining-=take
