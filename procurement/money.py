"""Recorded snapshot amounts, not an invoice/tax engine.

No product tax treatment, tax-inclusive price, discount or fee is registered in
current schema. Unknown tax/payable values must stay unknown in every output.
Existing snapshot rounding is preserved; no historical amounts are rewritten.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError

TAX_PENDING = '확인 필요 (세금 기준 미등록)'


def recorded_amount(item):
    amount = Decimal(str(item.estimated_price))
    if not amount.is_finite() or amount < 0:
        raise ValidationError('기록된 발주 금액이 올바르지 않습니다.')
    return amount


def accepted_amount(item, accepted):
    amount = recorded_amount(item)
    quantity = Decimal(str(accepted))
    # inspect_item already permits a documented overdelivery. Reporting must
    # preserve that policy rather than reject an existing accepted receipt.
    if not quantity.is_finite() or quantity < 0:
        raise ValidationError('합격 수량은 유한한 0 이상 수량이어야 합니다.')
    return amount * quantity / item.required_qty if item.required_qty else Decimal('0')


def review_totals(items):
    return {'recorded_total': sum((recorded_amount(item) for item in items), Decimal('0')),
            'tax_amount': None, 'payable_amount': None, 'tax_note': TAX_PENDING}
