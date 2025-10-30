from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from catalog.models import Product
from .models import CartItem
from .utils import get_or_create_cart
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

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


from decimal import Decimal
import json
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

def _recalc(cart):
    items = list(cart.items.select_related("product"))
    subtotal = sum((x.unit_price_snapshot * x.qty for x in items), Decimal("0.00"))
    shipping_total = Decimal("0.00")
    total = (subtotal + shipping_total).quantize(Decimal("0.01"))
    qty_total = sum((x.qty for x in items), 0)
    return items, subtotal, shipping_total, total, qty_total

def cart_summary_fragment(request):
    cart = get_or_create_cart(request)
    _, subtotal, shipping_total, total, _ = _recalc(cart)
    html = render_to_string("cart/_summary.html", {
        "subtotal": subtotal, "shipping_total": shipping_total, "total": total
    }, request=request)
    return HttpResponse(html)

def cart_count_fragment(request):
    cart = get_or_create_cart(request)
    *_, qty_total = _recalc(cart)
    html = render_to_string("cart/_cart_count.html", {"qty": qty_total}, request=request)
    return HttpResponse(html)

@require_POST
def update_item(request):
    try:
        item_id = int(request.POST.get("item_id", "0"))
        qty = int(request.POST.get("qty", "1"))
        if qty < 1:
            qty = 1
    except ValueError:
        return HttpResponseBadRequest("Bad qty")

    cart = get_or_create_cart(request)
    it = cart.items.select_related("product").filter(id=item_id).first()
    if not it:
        return HttpResponseBadRequest("No item")

    # проверка остатков
    if it.product.in_stock < qty:
        qty = it.product.in_stock
        if qty < 1:
            # удаляем строку и просто перезагружаем страницу корзины (надёжно)
            it.delete()
            resp = HttpResponseRedirect("/cart/")
            resp["HX-Redirect"] = "/cart/"
            return resp

    it.qty = qty
    it.save(update_fields=["qty", "updated_at"])

    # пересчитать
    items, subtotal, shipping_total, total, qty_total = _recalc(cart)

    # вернуть обновлённую строку
    row_html = render_to_string("cart/_row.html", {"it": it}, request=request)
    resp = HttpResponse(row_html)

    # триггерим «пересчитать фрагменты» (итоги и бейдж в шапке)
    # оба фрагмента на странице подписаны на это событие
    resp["HX-Trigger"] = json.dumps({"cart-recalc": 1})
    return resp
