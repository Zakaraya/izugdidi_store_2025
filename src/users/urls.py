from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("account/", views.account_hub, name="account_hub"),                        # каркас + активная вкладка
    path("account/tab/profile/", views.account_tab_profile, name="account_tab_profile"),  # вкладка Профиль (GET/POST)
    path("account/tab/orders/", views.account_tab_orders, name="account_tab_orders"),     # вкладка Заказы
    path("account/orders/", views.my_orders, name="my_orders"),                     # оставить для совместимости (старый маршрут)
    path("accounts/signup/", views.signup, name="signup"),
]
