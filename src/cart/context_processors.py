from .utils import get_or_create_cart

def cart_info(request):
    try:
        cart = get_or_create_cart(request)
        count = sum(i.qty for i in cart.items.all())
        total = sum((i.unit_price_snapshot * i.qty for i in cart.items.all()), 0)
    except Exception:
        count = 0
        total = 0
    return {"cart_count": count, "cart_total": total}
