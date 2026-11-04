"""Compatibility formatting; packaging requires an explicit SupplySpecification.
Free text spec/category must never imply a package size or mass-volume conversion.
"""
from .workflow import quantity, convert


def parse_spec_unit_and_qty(spec_str, total_qty_val, unit_str='', category='', *, specification=None):
    total = quantity(total_qty_val if total_qty_val is not None else 0)
    if specification is None:
        return total, unit_str
    size = convert(quantity(specification.base_quantity, positive=True), specification.base_unit, unit_str)
    return total / size, specification.order_unit


def format_qty(val):
    return format(quantity(val).normalize(), 'f')


def calculate_physical_units(spec_str, total_qty_val, unit_str='', category='', *, specification=None):
    value, unit = parse_spec_unit_and_qty(spec_str, total_qty_val, unit_str, category, specification=specification)
    return f'{format_qty(value)} {unit}'.strip()
