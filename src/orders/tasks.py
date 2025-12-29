from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Order


def _send_order_email(order_id, template_name, subject):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return

    context = {
        'order': order,
        'domain': '127.0.0.1:8000',  # Для локальных тестов
        'protocol': 'http',
    }

    html_content = render_to_string(f'emails/{template_name}.html', context)
    text_content = render_to_string(f'emails/{template_name}.txt', context)

    msg = EmailMultiAlternatives(
        subject=f"{subject} #{order.id}",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task
def send_order_created_email(order_id):
    _send_order_email(order_id, 'order_created', _('Ваш заказ принят'))


@shared_task
def send_order_paid_email_task(order_id):
    _send_order_email(order_id, 'order_paid', _('Заказ оплачен'))


@shared_task
def run_payment_reminders():
    """Задача для Celery Beat: ищем неоплаченные заказы"""
    now = timezone.now()
    # Напоминаем через 24 часа после создания
    remind_threshold = now - timedelta(hours=24)

    # Ищем заказы PENDING, которые созданы более 24 часов назад
    # и по которым еще не отправляли напоминание (можно добавить поле в модель, если нужно)
    orders = Order.objects.filter(
        status=Order.Status.PENDING,
        created_at__lte=remind_threshold,
        created_at__gte=now - timedelta(hours=48)  # Чтобы не напоминать совсем старым
    )

    for order in orders:
        _send_order_email(order.id, 'payment_reminder', _('Напоминание об оплате'))