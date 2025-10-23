from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from cart.utils import get_or_create_cart
from .forms import CheckoutForm
from .models import Coupon, Order, OrderItem
from .tasks import send_order_placed_email

def _calc_discount(subtotal: Decimal, coupon: Coupon) -> Decimal:
    if not coupon:
        return Decimal("0.00")
    if coupon.type == Coupon.Type.PERCENT:
        return (subtotal * coupon.value / Decimal("100")).quantize(Decimal("0.01"))
    return min(coupon.value, subtotal).quantize(Decimal("0.01"))

def _get_valid_coupon_or_none(code: str, user, email: str, subtotal: Decimal):
    if not code:
        return None, "Промокод не указан."
    try:
        coupon = Coupon.objects.get(code__iexact=code.strip())
    except Coupon.DoesNotExist:
        return None, "Промокод не найден."
    if not coupon.is_valid_now():
        return None, "Срок действия промокода истёк или он не активен."
    if subtotal < coupon.min_total:
        return None, f"Минимальная сумма для применения промокода: {coupon.min_total}."
    if coupon.usage_limit_total is not None:
        used_total = Order.objects.filter(coupon=coupon).count()
        if used_total >= coupon.usage_limit_total:
            return None, "Лимит использования промокода исчерпан."
    if coupon.usage_limit_per_user is not None:
        if user and getattr(user, "is_authenticated", False):
            used_by_user = Order.objects.filter(coupon=coupon, user=user).count()
        else:
            used_by_user = Order.objects.filter(coupon=coupon, email=email).count()
        if used_by_user >= coupon.usage_limit_per_user:
            return None, "Вы уже использовали этот промокод максимально допустимое число раз."
    return coupon, None

def checkout(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related("product").all())
    subtotal = sum((i.unit_price_snapshot * i.qty for i in items), Decimal("0.00"))
    shipping_total = Decimal("0.00")

    # применённый купон из сессии (если есть)
    applied_code = request.session.get("applied_coupon_code", "")
    initial = {}
    if request.user.is_authenticated:
        initial.update({
            "email": request.user.email,
            "customer_name": request.user.get_full_name() or request.user.username,
        })
    if applied_code:
        initial["promo_code"] = applied_code

    # предварительные значения для отображения
    coupon = None
    discount_total = Decimal("0.00")

    if request.method == "POST":
        action = request.POST.get("action", "").strip()  # "apply" или "place"
        form = CheckoutForm(request.POST)

        # Обработка применения купона — не оформляем заказ
        if action == "apply":
            # Разрешаем применять купон даже если контактные поля пустые:
            promo_code = request.POST.get("promo_code", "").strip()
            # Для подсчёта лимита per-user используем email (если введён) или пустую строку
            tmp_email = request.POST.get("email", "").strip()
            coupon, err = _get_valid_coupon_or_none(promo_code, request.user, tmp_email, subtotal)
            if coupon is None:
                messages.error(request, err)
                # очищаем ранее применённый код
                request.session.pop("applied_coupon_code", None)
            else:
                request.session["applied_coupon_code"] = coupon.code
                messages.success(request, "Промокод применён.")
                discount_total = _calc_discount(subtotal, coupon)
            # Перерисовываем страницу с формой (с тем, что ввёл пользователь)
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

        # Оформление заказа
        if action == "place":
            if form.is_valid():
                customer_name = form.cleaned_data["customer_name"]
                email = form.cleaned_data["email"]
                phone = form.cleaned_data["phone"]
                shipping_address = form.cleaned_data["shipping_address"].strip()
                billing_same = form.cleaned_data["billing_same"]
                billing_address = form.cleaned_data["billing_address"].strip() if not billing_same else shipping_address
                promo_code = form.cleaned_data["promo_code"].strip()

                coupon = None
                discount_total = Decimal("0.00")
                if promo_code:
                    coupon, err = _get_valid_coupon_or_none(promo_code, request.user, email, subtotal)
                    if coupon is None:
                        messages.error(request, err)
                        # не оформляем заказ — заново показываем страницу
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
                else:
                    # если поля промокода пусты, но в сессии уже есть код — применим его
                    if applied_code:
                        coupon, _ = _get_valid_coupon_or_none(applied_code, request.user, email, subtotal)
                        if coupon:
                            discount_total = _calc_discount(subtotal, coupon)

                if not items:
                    messages.error(request, "Корзина пуста.")
                    return redirect("cart:detail")

                total = (subtotal - discount_total + shipping_total).quantize(Decimal("0.01"))
                if total < 0:
                    total = Decimal("0.00")

                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        status=Order.Status.PENDING,
                        total=total,
                        discount_total=discount_total,
                        shipping_total=shipping_total,
                        currency="GEL",
                        email=email,
                        phone=phone,
                        customer_name=customer_name,
                        shipping_address_json={"address": shipping_address},
                        billing_address_json={"address": billing_address},
                        coupon=coupon,
                        placed_at=timezone.now(),
                    )
                    for it in items:
                        OrderItem.objects.create(
                            order=order,
                            product=it.product,
                            title_snapshot=(
                                it.product.safe_translation_getter("title", any_language=True)
                                or str(it.product)
                            ),
                            qty=it.qty,
                            unit_price_snapshot=it.unit_price_snapshot,
                        )
                        if it.product.in_stock >= it.qty:
                            it.product.in_stock -= it.qty
                            it.product.save(update_fields=["in_stock", "updated_at"])
                    cart.items.all().delete()

                context = {
                    "order": order,
                    "request_scheme": request.scheme,
                    "request_host": request.get_host(),
                }
                try:
                    send_order_placed_email.delay(order.id, order.email, context)
                except Exception as exc:
                    pass
                messages.success(request, "Заказ создан. Спасибо!")
                return redirect("orders:success", pk=order.pk)

            # форма невалидна — показать ошибки
            messages.error(request, "Проверьте корректность данных.")
            # падать дальше в общий рендер ниже (с подсказками)

    else:
        form = CheckoutForm(initial=initial)

    # Отображение (GET или неуспешный POST)
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
        "applied_code": applied_code,
    })

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