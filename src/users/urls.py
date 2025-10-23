from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("account/orders/", views.my_orders, name="my_orders"),
    path("accounts/signup/", views.signup, name="signup"),
]
