from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<int:order_id>/", views.pay_page, name="pay_page"),
    path("payments/mockpay/callback/", views.mockpay_return, name="mockpay_return"),
    path("payments/mockpay/webhook/", views.mockpay_webhook, name="mockpay_webhook"),
]
