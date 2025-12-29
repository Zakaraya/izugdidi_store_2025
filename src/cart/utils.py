from .models import Cart
from .services import _get_or_create_cart_for_request, SESSION_CART_KEY

def get_or_create_cart(request):
    """
    Получает или создаёт корзину для пользователя.
    Объединяет гостевую корзину с корзиной пользователя после входа.
    """
    # Сначала получим корзину, используя централизованную логику
    cart = _get_or_create_cart_for_request(request)

    # Логика слияния корзин при входе пользователя
    if request.user.is_authenticated:
        session_key = request.session.pop(SESSION_CART_KEY, None)
        if session_key:
            try:
                guest_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
                if guest_cart.id != cart.id:
                    # Переносим товары из гостевой корзины в корзину пользователя
                    for item in guest_cart.items.all():
                        target_item, created = cart.items.get_or_create(
                            product=item.product,
                            defaults={
                                "qty": item.qty,
                                "unit_price_snapshot": item.unit_price_snapshot
                            }
                        )
                        if not created:
                            target_item.qty += item.qty
                            target_item.save(update_fields=["qty", "updated_at"])
                    guest_cart.delete()
            except Cart.DoesNotExist:
                pass  # Гостевой корзины не существует, ничего не делаем

    return cart

# def ensure_session_key(request):
#     if not request.session.session_key:
#         request.session.save()