from decimal import Decimal
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from cart.utils import get_or_create_cart
from .forms import CheckoutForm
from .models import Coupon, Order, OrderItem
# from .tasks import send_order_placed_email
from django.contrib.auth.decorators import login_required
from .tasks import send_order_created_email


def _calc_discount(subtotal: Decimal, coupon: Coupon) -> Decimal:
    if not coupon:
        return Decimal("0.00")
    if coupon.type == Coupon.Type.PERCENT:
        return (subtotal * coupon.value / Decimal("100")).quantize(Decimal("0.01"))
    return min(coupon.value, subtotal).quantize(Decimal("0.01"))

def _get_valid_coupon_or_none(code: str, user, email: str, subtotal: Decimal):
    if not code:
        return None, "The promocode is not specified."
    try:
        coupon = Coupon.objects.get(code__iexact=code.strip())
    except Coupon.DoesNotExist:
        return None, "The promocode was not found."
    if not coupon.is_valid_now():
        return None, "The promocode has expired or is inactive."
    if subtotal < coupon.min_total:
        return None, f"The minimum amount to apply the promocode: {coupon.min_total}."
    if coupon.usage_limit_total is not None:
        used_total = Order.objects.filter(coupon=coupon).count()
        if used_total >= coupon.usage_limit_total:
            return None, "The promocode usage limit has been reached."
    if coupon.usage_limit_per_user is not None:
        if user and getattr(user, "is_authenticated", False):
            used_by_user = Order.objects.filter(coupon=coupon, user=user).count()
        else:
            used_by_user = Order.objects.filter(coupon=coupon, email=email).count()
        if used_by_user >= coupon.usage_limit_per_user:
            return None, "You have already used this promocode as many times as possible."
    return coupon, None

def checkout(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related("product"))
    subtotal = sum((i.unit_price_snapshot * i.qty for i in items), Decimal("0.00"))
    shipping_total = Decimal("0.00")

    # применённый купон из сессии (если есть)
    applied_code = request.session.get("applied_coupon_code", "")

    # initial значениями заполняем форму на GET и при невалидном POST
    initial = {}
    if request.user.is_authenticated:
        initial.update({
            "email": request.user.email or "",
            "customer_name": (request.user.get_full_name() or request.user.username),
            "phone": getattr(getattr(request.user, "profile", None), "phone", ""),
        })
    if applied_code:
        initial["promo_code"] = applied_code

    # значения по умолчанию для отображения
    coupon = None
    discount_total = Decimal("0.00")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()  # "apply" или "place"
        form = CheckoutForm(request.POST)

        # 1) Применение купона — не требуем валидности всей формы
        if action == "apply":
            promo_code = (request.POST.get("promo_code") or "").strip()
            tmp_email = (request.POST.get("email") or "").strip()  # для per-user лимитов

            coupon, err = _get_valid_coupon_or_none(promo_code, request.user, tmp_email, subtotal)
            if coupon is None:
                messages.error(request, err)
                request.session.pop("applied_coupon_code", None)
            else:
                request.session["applied_coupon_code"] = coupon.code
                discount_total = _calc_discount(subtotal, coupon)
                messages.success(request, "The promocode has been applied.")

            total = (subtotal - discount_total + shipping_total).quantize(Decimal("0.01"))
            return render(request, "orders/checkout.html", {
                "form": form,  # показываем то, что ввёл пользователь
                "items": items,
                "subtotal": subtotal,
                "shipping_total": shipping_total,
                "discount_total": discount_total,
                "total": total,
                "applied_code": request.session.get("applied_coupon_code", ""),
            })

        # 2) Оформление заказа — валидируем форму и создаём заказ
        if action == "place":
            if not form.is_valid():
                messages.error(request, "Check the correctness of the data.")
            else:
                email = form.cleaned_data["email"]
                # финальное определение купона: приоритет — то, что ввёл пользователь; иначе — купон из сессии
                promo_code = (form.cleaned_data.get("promo_code") or "").strip()
                coupon = None
                discount_total = Decimal("0.00")

                if promo_code:
                    coupon, err = _get_valid_coupon_or_none(promo_code, request.user, email, subtotal)
                    if coupon is None:
                        messages.error(request, err)
                        total = (subtotal - discount_total + shipping_total).quantize(Decimal("0.01"))
                        return render(request, "orders/checkout.html", {
                            "form": form,
                            "items": items,
                            "subtotal": subtotal,
                            "shipping_total": shipping_total,
                            "discount_total": discount_total,
                            "total": total,
                            "applied_code": request.session.get("applied_coupon_code", ""),
                        })
                    discount_total = _calc_discount(subtotal, coupon)
                    request.session["applied_coupon_code"] = coupon.code
                elif applied_code:
                    # в форме промокод пуст, но в сессии есть — пытаемся применить его
                    coupon, _ = _get_valid_coupon_or_none(applied_code, request.user, email, subtotal)
                    if coupon:
                        discount_total = _calc_discount(subtotal, coupon)

                if not items:
                    messages.error(request, "The shopping cart is empty.")
                    return redirect("cart:detail")

                total = (subtotal - discount_total + shipping_total).quantize(Decimal("0.01"))
                if total < 0:
                    total = Decimal("0.00")

                with transaction.atomic():
                    # ВАЖНО: адреса и способ доставки уже соберутся в save() формы
                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user
                    else:
                        order.guest_email = form.cleaned_data['email']
                    order.status = Order.Status.PENDING
                    order.total = total
                    order.discount_total = discount_total
                    order.shipping_total = shipping_total
                    order.currency = "GEL"
                    order.coupon = coupon
                    order.placed_at = timezone.now()
                    order.save()

                    # переноcим позиции корзины
                    for it in items:
                        OrderItem.objects.create(
                            order=order,
                            product=it.product,
                            title_snapshot=(it.product.safe_translation_getter("title", any_language=True) or str(it.product)),
                            qty=it.qty,
                            unit_price_snapshot=it.unit_price_snapshot,
                        )
                        if it.product.in_stock >= it.qty:
                            it.product.in_stock -= it.qty
                            it.product.save(update_fields=["in_stock", "updated_at"])

                    # очищаем корзину
                    cart.items.all().delete()

                # письмо — опционально
                # try:
                #     context = {"order": order, "request_scheme": request.scheme, "request_host": request.get_host()}
                #     send_order_placed_email.delay(order.id, order.email, context)
                # except Exception:
                #     pass
                # send_order_created_email.delay(order.id)
                send_order_created_email(order.id)
                messages.success(request, "The order has been created. Thanks!")
                return redirect("orders:success", pk=order.pk)

        # если action неожиданный или форма невалидна — падаем к общему рендеру ниже
    else:
        form = CheckoutForm(initial=initial)

    # GET или неуспешный POST: пересчёт скидки по купону из сессии (если есть)
    if applied_code:
        coupon, err = _get_valid_coupon_or_none(applied_code, request.user, initial.get("email", ""), subtotal)
        if coupon:
            discount_total = _calc_discount(subtotal, coupon)

    total = (subtotal - discount_total + shipping_total).quantize(Decimal("0.01"))
    return render(request, "orders/checkout.html", {
        "form": form,
        "items": items,
        "subtotal": subtotal,
        "shipping_total": shipping_total,
        "discount_total": discount_total,
        "total": total,
        "applied_code": request.session.get("applied_coupon_code", "") or "",
    })

@login_required
def order_track(request, pk: int):
    order = get_object_or_404(Order, pk=pk)
    flow = ["pending", "paid", "processing", "shipped", "delivered"]
    def reached(step):
        try:
            return flow.index(order.status) >= flow.index(step)
        except ValueError:
            return False
    ctx = {
        "order": order,
        "step_pending": reached("pending"),
        "step_paid": reached("paid"),
        "step_processing": reached("processing"),
        "step_shipped": reached("shipped"),
        "step_delivered": reached("delivered"),
    }
    return render(request, "orders/order_track.html", ctx)

def order_success(request, pk: int):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "orders/order_success.html", {"order": order})

def checkout_address_fields(request):
    """
    Возвращает только кусок HTML с адресными полями в зависимости от выбранного метода.
    Вызывается HTMX при смене delivery_method.
    """
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")
    method = request.GET.get("delivery_method", Order.DELIVERY_PICKUP)
    form = CheckoutForm(initial={"delivery_method": method})
    html = render_to_string("orders/_address_fields.html", {"form": form, "method": method}, request=request)
    return HttpResponse(html)