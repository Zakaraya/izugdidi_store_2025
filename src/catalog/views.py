from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from .models import Category, Product, Brand
from django.template.loader import render_to_string
from django.http import HttpResponse

def product_list(request, category_slug=None):
    qs = Product.objects.filter(is_published=True, in_stock__gt=0).select_related("brand", "category")

    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        qs = qs.filter(category=category)

    # Фильтры из querystring
    brand = request.GET.get("brand", "").strip()
    storage = request.GET.get("storage", "").strip()
    cond = request.GET.get("cond", "").strip()
    price_min = request.GET.get("price_min", "").strip()
    price_max = request.GET.get("price_max", "").strip()
    search = request.GET.get("q", "").strip()
    ordering = request.GET.get("o", "").strip()  # price_asc | price_desc | newest

    if brand:
        qs = qs.filter(brand__slug=brand)
    if storage.isdigit():
        qs = qs.filter(storage_gb=int(storage))
    if cond in {"A", "B", "C"}:
        qs = qs.filter(condition=cond)
    if price_min.replace(".", "", 1).isdigit():
        qs = qs.filter(price__gte=price_min)
    if price_max.replace(".", "", 1).isdigit():
        qs = qs.filter(price__lte=price_max)
    if search:
        qs = qs.filter(
            Q(translations__title__icontains=search) |
            Q(model_name__icontains=search) |
            Q(color__icontains=search) |
            Q(sku__icontains=search)
        ).distinct()

    if ordering == "price_asc":
        qs = qs.order_by("price")
    elif ordering == "price_desc":
        qs = qs.order_by("-price")
    else:
        qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "category": category,
        "page_obj": page_obj,
        "brands": Brand.objects.order_by("name"),
        "storages": [64, 128, 256, 512],
        "current": {
            "brand": brand, "storage": storage, "cond": cond,
            "price_min": price_min, "price_max": price_max,
            "q": search, "o": ordering,
        },
    }
    if request.headers.get("HX-Request") == "true":
        html = render_to_string("catalog/_product_grid.html", ctx, request=request)
        return HttpResponse(html)
    return render(request, "catalog/product_list.html", ctx)

def product_detail(request, base_slug):
    product = get_object_or_404(
        Product.objects.select_related("brand", "category").prefetch_related("images"),
        base_slug=base_slug, is_published=True
    )
    related = Product.objects.filter(
        brand=product.brand, category=product.category, is_published=True
    ).exclude(id=product.id).order_by("-created_at")[:8]
    return render(request, "catalog/product_detail.html", {"product": product, "related": related})
