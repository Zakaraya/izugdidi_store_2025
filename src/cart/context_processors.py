from .utils import get_or_create_cart
from .services import _get_or_create_cart_for_request
from .models import CartItem

def cart_info(request):
    try:
        cart = get_or_create_cart(request)
        count = sum(i.qty for i in cart.items.all())
        total = sum((i.unit_price_snapshot * i.qty for i in cart.items.all()), 0)
    except Exception:
        count = 0
        total = 0
    return {"cart_count": count, "cart_total": total}

def cart_header(request):
    try:
        cart = _get_or_create_cart_for_request(request)
    except Exception:
        return {"cart_items_count": 0}

    # Суммируем qty (даже если позиций несколько)
    total = CartItem.objects.filter(cart=cart).values_list("qty", flat=True)
    return {"cart_items_count": sum(total) if total else 0}