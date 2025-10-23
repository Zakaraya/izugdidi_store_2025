from .models import Cart

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # если у гостя была корзина по session_key — сольём
        sk = request.session.session_key
        if sk:
            try:
                guest_cart = Cart.objects.get(session_key=sk, user__isnull=True)
            except Cart.DoesNotExist:
                guest_cart = None
            if guest_cart and guest_cart.id != cart.id:
                # перенесём позиции
                for item in guest_cart.items.all():
                    target = cart.items.filter(product=item.product).first()
                    if target:
                        target.qty += item.qty
                        target.save(update_fields=["qty", "updated_at"])
                    else:
                        cart.items.create(
                            product=item.product,
                            qty=item.qty,
                            unit_price_snapshot=item.unit_price_snapshot
                        )
                guest_cart.delete()
        return cart
    # гость
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user=None)
    return cart
