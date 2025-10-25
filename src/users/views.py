from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

from orders.models import Order
from .forms import ProfileForm

@login_required
def my_orders(request):
    qs = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "users/my_orders.html", {"orders": qs})

def signup(request):
    if request.user.is_authenticated:
        return redirect("users:my_orders")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("users:my_orders")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def account_hub(request):
    # Определяем активную вкладку: ?tab=orders|profile (по умолчанию — orders)
    tab = request.GET.get("tab", "orders")
    if tab not in ("orders", "profile"):
        tab = "orders"
    # Загружаем содержимое активной вкладки сразу (SSR), чтобы без «мигания»
    if tab == "orders":
        tab_html = render_to_string("users/_tab_orders.html", {
            "orders": Order.objects.filter(user=request.user).order_by("-created_at")
        }, request=request)
    else:
        form = ProfileForm(user=request.user)
        tab_html = render_to_string("users/_tab_profile.html", {"form": form}, request=request)

    return render(request, "users/account_tabs.html", {"active_tab": tab, "tab_html": tab_html})

@login_required
def account_tab_orders(request):
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")
    html = render_to_string("users/_tab_orders.html", {
        "orders": Order.objects.filter(user=request.user).order_by("-created_at")
    }, request=request)
    return HttpResponse(html)

@login_required
def account_tab_profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            html = render_to_string("users/_tab_profile.html", {"form": ProfileForm(user=request.user)}, request=request)
            resp = HttpResponse(html)
            resp["X-Toast"] = "Профиль сохранён"
            return resp
    else:
        form = ProfileForm(user=request.user)
    html = render_to_string("users/_tab_profile.html", {"form": form}, request=request)
    return HttpResponse(html)