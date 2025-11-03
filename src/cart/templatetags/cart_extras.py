# cart/templatetags/cart_extras.py
from decimal import Decimal
from django import template

register = template.Library()

@register.filter
def mul(a, b):
    try:
        if a is None or b is None:
            return ""
        if not isinstance(a, Decimal):
            a = Decimal(str(a))
        if not isinstance(b, (int, Decimal)):
            b = Decimal(str(b))
        return a * b
    except Exception:
        return ""

@register.filter
def money(amount):
    if amount is None or amount == "":
        return "0,00"
    try:
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
    except Exception:
        return "0,00"
    s = f"{amount:.2f}"
    whole, frac = s.split(".")
    whole_spaced = " ".join([whole[max(i-3, 0):i] for i in range(len(whole), 0, -3)][::-1]) or "0"
    return f"{whole_spaced},{frac}"
