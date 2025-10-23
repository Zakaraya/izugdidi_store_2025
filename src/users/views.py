from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from orders.models import Order

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
