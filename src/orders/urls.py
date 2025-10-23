from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/success/", views.order_success, name="success"),
    path("orders/<int:pk>/track/", views.order_track, name="track"),
]
