# orders/emails.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.conf import settings


def send_order_email(order, template_name, subject):
    """
    Универсальная функция для отправки HTML-писем
    """
    context = {
        'order': order,
        'protocol': 'https' if not settings.DEBUG else 'http',
        'domain': 'yourdomain.com' if not settings.DEBUG else '127.0.0.1:8000',
    }

    html_content = render_to_string(f'emails/{template_name}.html', context)
    text_content = render_to_string(f'emails/{template_name}.txt', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()