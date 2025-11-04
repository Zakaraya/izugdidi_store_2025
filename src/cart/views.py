from decimal import Decimal, InvalidOperation
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.translation import gettext
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, JsonResponse
from catalog.models import Product
from .models import CartItem
from .utils import get_or_create_cart
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.template import engines
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from .services import get_cart, _get_or_create_cart_for_request

def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("product").all()
    subtotal = sum((i.unit_price_snapshot * i.qty for i in items), Decimal("0.00"))
    ctx = {"cart": cart, "items": items, "subtotal": subtotal}
    return render(request, "cart/cart_detail.html", ctx)

def _render_badge_oob(total_qty: int) -> str:
    inner = render_to_string("cart/_badge.html", {"qty_total": total_qty})
    return f'<span id="cart-badge" hx-swap-oob="true">{inner}</span>'

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
    _, items, _ = get_cart(request)
    total_qty = sum(i.qty for i in items)
    if request.headers.get("HX-Request") == "true":
        oob = _render_badge_oob(total_qty)
        resp = HttpResponseRedirect("/cart/")
        resp["HX-Redirect"] = request.META.get("HTTP_REFERER", "/")
        resp = HttpResponse(oob, content_type="text/html; charset=utf-8")
        resp["X-Toast"] = "Product added to cart"
        return resp
    messages.success(request, "The product has been added to the cart.")
    return redirect("cart:detail")

@require_POST
def cart_update(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    qty = int(request.POST.get("qty", "1"))
    if qty <= 0:
        item.delete()
        messages.info(request, "Тhe product has been removed from the shopping cart.")
    else:
        item.qty = qty
        item.save(update_fields=["qty", "updated_at"])
        messages.success(request, "The quantity has been updated.")
    if request.headers.get("HX-Request") == "true":
        resp = redirect("cart:detail")
        resp["X-Toast"] = "Quantity updated"  # или "Товар удалён"
        return resp
    return redirect("cart:detail")

@require_POST
def cart_remove(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    messages.info(request, "The product has been deleted.")
    if request.headers.get("HX-Request") == "true":
        resp = redirect("cart:detail")
        resp["X-Toast"] = "Quantity updated"  # или "Товар удалён"
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
    cart = get_or_create_cart(request)
    try:
        item_id = int(request.POST.get("item_id", "0"))
        qty_str = request.POST.get("qty")
        qty = int(qty_str) if qty_str and qty_str.isdigit() else 1
        if qty < 1: qty = 1
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Bad request")

    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if item.product.in_stock < qty:
        qty = item.product.in_stock
        if qty < 1:
            item.delete()
            response = HttpResponse(status=204);
            response['HX-Redirect'] = request.path_info;
            return response

    item.qty = qty
    item.save(update_fields=["qty"])

    # Вызываем вашу существующую функцию _recalc
    _, subtotal, _, _, qty_total = _recalc(cart)

    # Рендерим все 4 фрагмента, которые нужно обновить
    row_html = render_to_string("cart/_row.html", {"it": item}, request=request)
    card_html = render_to_string("cart/_card.html", {"it": item}, request=request)
    summary_html = render_to_string("cart/_summary.html", {"subtotal": subtotal}, request=request)
    badge_html = render_to_string("cart/_badge.html", {"qty_total": qty_total}, request=request)

    # Собираем все в один ответ. HTMX сам найдет элементы по ID и заменит их.
    return HttpResponse(row_html + card_html + summary_html + badge_html)




def _render_money_html(amount, currency):
    tpl = engines["django"].from_string(
        "{% load cart_extras %}{{ amount|money }} {{ currency }}"
    )
    return tpl.render({"amount": amount, "currency": currency})

def _render_badge_html(total_qty: int) -> str:
    return render_to_string("cart/_badge.html", {"qty_total": total_qty})

@require_POST
@login_required
def update_item_qty(request, item_id: int):
    try:
        qty_raw = request.POST.get("qty")
        qty = int(qty_raw)
        if qty < 1:
            raise ValueError("Quantity must be >= 1")
    except (TypeError, ValueError, InvalidOperation):
        return HttpResponseBadRequest("Invalid quantity")

    try:
        item = CartItem.objects.select_related("product").get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return HttpResponseBadRequest("Item not found")

    # при желании можно проверять наличие stock и т.п.
    item.qty = qty
    item.save(update_fields=["qty"])

    cart_obj, items, subtotal = get_cart(request)
    total_qty = sum(i.qty for i in items)

    item_total = (item.unit_price_snapshot or Decimal("0")) * item.qty
    item_total_html = _render_money_html(item_total, item.product.currency)

    summary_html = render_to_string("cart/_summary.html", {"subtotal": subtotal}, request=request)
    badge_html = _render_badge_html(total_qty)

    return JsonResponse({
        "ok": True,
        "item_id": item.id,
        "item_total_html": item_total_html,
        "summary_html": summary_html,
        "badge_html": badge_html,
        "total_qty": total_qty,
        "qty": item.qty,
    })


@require_POST
def remove_item(request, item_id: int):
    cart = _get_or_create_cart_for_request(request)

    try:
        item = CartItem.objects.select_related("product").get(id=item_id, cart=cart)
    except CartItem.DoesNotExist:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "Item not found"}, status=400)
        return HttpResponseBadRequest("Item not found")

    item.delete()

    cart_obj, items, subtotal = get_cart(request)
    total_qty = sum(i.qty for i in items)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        summary_html = render_to_string("cart/_summary.html", {"subtotal": subtotal}, request=request)
        badge_html = _render_badge_html(total_qty)
        return JsonResponse({
            "ok": True,
            "removed_id": item_id,
            "items_count": len(items),
            "summary_html": summary_html,
            "badge_html": badge_html,
            "total_qty": total_qty,
        })

    messages.success(request, gettext("The product has been removed from the shopping cart."))
    return HttpResponseRedirect(reverse("cart:detail"))


def cart_page(request):
    cart, items, subtotal = get_cart(request)
    return render(request, "cart/cart.html", {"items": items, "subtotal": subtotal})