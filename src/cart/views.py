from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseRedirect
from catalog.models import Product
from .models import CartItem
from .utils import get_or_create_cart

def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("product").all()
    subtotal = sum((i.unit_price_snapshot * i.qty for i in items), Decimal("0.00"))
    ctx = {"cart": cart, "items": items, "subtotal": subtotal}
    return render(request, "cart/cart_detail.html", ctx)

@require_POST
def cart_add(request):
    cart = get_or_create_cart(request)
    pid = int(request.POST.get("product_id", "0"))
    product = get_object_or_404(Product, pk=pid, is_published=True)
    qty = int(request.POST.get("qty", "1"))
    item, created = cart.items.get_or_create(product=product, defaults={
        "qty": qty,
        "unit_price_snapshot": product.price
    })
    if not created:
        item.qty += qty
        item.save(update_fields=["qty", "updated_at"])
    if request.headers.get("HX-Request") == "true":
        resp = HttpResponseRedirect("/cart/")
        resp["HX-Redirect"] = request.META.get("HTTP_REFERER", "/")
        resp["X-Toast"] = "Товар добавлен в корзину"
        return resp
    messages.success(request, "Товар добавлен в корзину.")
    return redirect("cart:detail")

@require_POST
def cart_update(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    qty = int(request.POST.get("qty", "1"))
    if qty <= 0:
        item.delete()
        messages.info(request, "Товар удалён из корзины.")
    else:
        item.qty = qty
        item.save(update_fields=["qty", "updated_at"])
        messages.success(request, "Количество обновлено.")
    if request.headers.get("HX-Request") == "true":
        resp = redirect("cart:detail")
        resp["X-Toast"] = "Количество обновлено"  # или "Товар удалён"
        return resp
    return redirect("cart:detail")

@require_POST
def cart_remove(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    messages.info(request, "Товар удалён.")
    if request.headers.get("HX-Request") == "true":
        resp = redirect("cart:detail")
        resp["X-Toast"] = "Количество обновлено"  # или "Товар удалён"
        return resp
    return redirect("cart:detail")
