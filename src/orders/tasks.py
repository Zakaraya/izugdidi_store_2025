from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order

def _build_context(order: Order, scheme: str, host: str) -> dict:
    return {
        "order": order,
        "request_scheme": scheme,
        "request_host": host,
    }

@shared_task
def send_order_placed_email(order_id: int, scheme: str, host: str):
    order = Order.objects.get(pk=order_id)
    subject = f"Order #{order.id} placed"
    body = render_to_string("email/order_placed.txt", _build_context(order, scheme, host))
    send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None), [order.email], fail_silently=False)

@shared_task
def send_order_paid_email(order_id: int, scheme: str, host: str):
    order = Order.objects.get(pk=order_id)
    subject = f"Order #{order.id} paid"
    body = render_to_string("email/order_paid.txt", _build_context(order, scheme, host))
    send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None), [order.email], fail_silently=False)
