from django.urls import path
from . import views

app_name = "cms"

urlpatterns = [
    path("", views.home, name="home"),
    path("contacts/", views.contacts, name="contacts"),
    path("delivery/", views.delivery, name="delivery"),
    path("warranty/", views.warranty, name="warranty"),
    path("faq/", views.faq, name="faq"),
]
