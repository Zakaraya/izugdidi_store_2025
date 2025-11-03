# cart/services.py
from decimal import Decimal
from django.utils.crypto import get_random_string
from .models import Cart, CartItem

SESSION_CART_KEY = "cart_session_key"

def _ensure_session_key(request) -> str:
    """
    Возвращает и при необходимости создаёт стабильный session_key для гостя.
    """
    key = request.session.get(SESSION_CART_KEY)
    if not key:
        key = get_random_string(32)
        request.session[SESSION_CART_KEY] = key
    return key

def _get_or_create_cart_for_request(request) -> Cart:
    """
    Для авторизованного — Cart по user.
    Для гостя — Cart по session_key.
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        cart, _created = Cart.objects.get_or_create(user=user, defaults={})
        return cart

    session_key = _ensure_session_key(request)
    cart, _created = Cart.objects.get_or_create(user=None, session_key=session_key, defaults={})
    return cart

def get_cart(request):
    """
    Возвращает (cart, items_list, subtotal).
    """
    cart = _get_or_create_cart_for_request(request)
    items_qs = CartItem.objects.select_related("product").filter(cart=cart).order_by("id")

    subtotal = Decimal("0")
    items = []
    for it in items_qs:
        line = (it.unit_price_snapshot or Decimal("0")) * it.qty
        subtotal += line
        items.append(it)

    return cart, items, subtotal
