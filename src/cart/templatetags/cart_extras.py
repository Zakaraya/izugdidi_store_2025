from decimal import Decimal, ROUND_HALF_UP
from django import template

register = template.Library()

@register.filter
def money(value):
    """
    Форматирует число как денежное с 2 знаками после запятой.
    """
    try:
        q = Decimal("0.01")
        return Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP)
    except Exception:
        return value

@register.filter
def mul(value, arg):
    """
    Перемножает value * arg как Decimal и округляет до копеек.
    Пример: {{ 9.99|mul:3 }} -> 29.97
    """
    try:
        q = Decimal("0.01")
        return (Decimal(str(value)) * Decimal(str(arg))).quantize(q, rounding=ROUND_HALF_UP)
    except Exception:
        return ""
