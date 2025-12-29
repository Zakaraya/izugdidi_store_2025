from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from .models import Category, Product, Brand, Favorite
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from .context_processors import favorites_info

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
        ctx.update(favorites_info(request))
        html = render_to_string("catalog/_product_grid.html", ctx, request=request)
        return HttpResponse(html)
    return render(request, "catalog/product_list.html", ctx)

def product_detail(request, base_slug):
    product = get_object_or_404(
        Product.objects.select_related("brand", "category").prefetch_related("images"),
        base_slug=base_slug, is_published=True
    )
    related = Product.objects.filter(
        brand=product.brand, category=product.category, is_published=True, in_stock__gt=0
    ).exclude(id=product.id).order_by("-created_at")[:8]
    return render(request, "catalog/product_detail.html", {"product": product, "related": related})


@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Получаем или создаем сессию для анонима
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()

    filter_kwargs = {'product': product}
    if request.user.is_authenticated:
        filter_kwargs['user'] = request.user
    else:
        filter_kwargs['session_key'] = request.session.session_key

    fav_obj = Favorite.objects.filter(**filter_kwargs).first()

    if fav_obj:
        fav_obj.delete()
        is_fav = False
    else:
        Favorite.objects.create(**filter_kwargs)
        is_fav = True

    # Считаем новое общее количество
    if request.user.is_authenticated:
        total_favs = Favorite.objects.filter(user=request.user).count()
    else:
        total_favs = Favorite.objects.filter(session_key=request.session.session_key).count()

    if request.headers.get("HX-Request"):
        # Возвращаем обновленную кнопку и OOB-обновление для шапки
        badge_html = f'<span id="fav-badge" hx-swap-oob="true" class="badge">{total_favs}</span>'

        icon_fill = "currentColor" if is_fav else "none"
        btn_html = render_to_string("catalog/_fav_button.html",
                                    {'p': product, 'fav_ids': [product.id] if is_fav else []})

        return HttpResponse(btn_html + badge_html)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def favorite_list(request):
    # Получаем ID товаров из контекстного процессора (или дублируем логику здесь)
    if request.user.is_authenticated:
        fav_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
    else:
        s_key = request.session.session_key
        fav_ids = Favorite.objects.filter(session_key=s_key).values_list('product_id', flat=True) if s_key else []

    products = Product.objects.filter(id__in=fav_ids, is_published=True).select_related("brand", "category")

    return render(request, "catalog/favorites.html", {
        "page_obj": {"object_list": products},  # Эмулируем структуру для _product_grid
        "is_wishlist": True
    })