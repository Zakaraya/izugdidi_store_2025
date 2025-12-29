from decimal import Decimal
import hmac
import hashlib
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from orders.models import Order
from orders.tasks import send_order_paid_email_task

def _order_accessible(request, order: Order) -> bool:
    # Авторизованный видит свои заказы, гость — по id (для демо). В проде добавьте токен-доступ по email/кодам.
    if request.user.is_authenticated and order.user_id:
        return order.user_id == request.user.id
    return True

@require_http_methods(["GET", "POST"])
def pay_page(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)
    if not _order_accessible(request, order):
        messages.error(request, "There is no access to the order.")
        return redirect("cms:home")
    if order.status not in (Order.Status.PENDING, Order.Status.PROCESSING):
        messages.info(request, "This order no longer requires payment.")
        return redirect("orders:track", pk=order.id)

    if request.method == "POST":
        # Мок-оплата: сразу переводим в PAID и ставим placed_at, если нужно
        order.status = Order.Status.PAID
        if not order.placed_at:
            order.placed_at = timezone.now()
        order.save(update_fields=["status", "placed_at", "updated_at"])
        messages.success(request, "The payment was successful.")
        context = {
            "order": order,
            "request_scheme": request.scheme,
            "request_host": request.get_host(),
        }
        try:
            # send_order_paid_email.delay(order.id, order.email, context)
            send_order_paid_email_task.delay(order.id)
        except Exception as e:
            pass
        return redirect("orders:track", pk=order.id)

    return render(request, "payments/pay_page.html", {"order": order})

@require_http_methods(["GET"])
def mockpay_return(request):
    # Страница возврата от «провайдера» — просто редирект на трекинг
    oid = request.GET.get("order_id")
    if not oid or not oid.isdigit():
        messages.error(request, "Incorrect response from the payment system.")
        return redirect("cms:home")
    return redirect("orders:track", pk=int(oid))

@require_http_methods(["POST"])
def mockpay_webhook(request):
    """
    Пример вебхука:
    - ожидаем поля: order_id, status, signature (HMAC SHA256 по "order_id|status" с секретом)
    - если status == "paid" и подпись корректна — ставим заказ в PAID
    """
    order_id = request.POST.get("order_id", "")
    status = request.POST.get("status", "")
    signature = request.POST.get("signature", "")

    if not (order_id.isdigit() and status and signature):
        return render(request, "payments/webhook_result.txt", {"text": "bad_request"}, content_type="text/plain")

    msg = f"{order_id}|{status}".encode()
    secret = settings.PAYMENTS["MOCKPAY_WEBHOOK_SECRET"].encode()
    digest = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(digest, signature):
        return render(request, "payments/webhook_result.txt", {"text": "invalid_signature"}, content_type="text/plain")

    order = get_object_or_404(Order, pk=int(order_id))

    if status == "paid" and order.status == Order.Status.PENDING:
        order.status = Order.Status.PAID
        if not order.placed_at:
            order.placed_at = timezone.now()
        order.save(update_fields=["status", "placed_at", "updated_at"])
        return render(request, "payments/webhook_result.txt", {"text": "ok"}, content_type="text/plain")

    return render(request, "payments/webhook_result.txt", {"text": "noop"}, content_type="text/plain")
