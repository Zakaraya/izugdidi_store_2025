from django.shortcuts import render
from catalog.models import Product

def home(request):
    latest = Product.objects.filter(is_published=True, in_stock__gt=0).order_by("-created_at")[:8]
    return render(request, "cms/home.html", {"latest": latest})

def contacts(request):
    return render(request, "cms/contacts.html")

def delivery(request):
    return render(request, "cms/delivery.html")

def warranty(request):
    return render(request, "cms/warranty.html")

def faq(request):
    return render(request, "cms/faq.html")
