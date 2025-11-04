from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import set_language
from django.http import HttpResponse

def healthz_view(_):
    # Никакой логики/редиректов, всегда 200 OK
    return HttpResponse("ok", content_type="text/plain", status=200)

urlpatterns = [
    # Технические и служебные пути
    path("healthz", healthz_view, name="healthz"),
    path("healthz/", healthz_view),
    path("admin/", admin.site.urls),
    path("i18n/setlang/", set_language, name="set_language"),

    # Основные приложения
    path("cms/", include(("cms.urls", "cms"), namespace="cms")),
    path("catalog/", include(("catalog.urls", "catalog"), namespace="catalog")),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
    path("payments/", include(("payments.urls", "payments"), namespace="payments")),
    path("users/", include(("users.urls", "users"), namespace="users")),
    path("accounts/", include("django.contrib.auth.urls")),

    # Главная страница — редирект на каталог
    path("", RedirectView.as_view(pattern_name="cms:home", permanent=False)),
]

# В DEBUG режиме — отдаём медиа локально
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
