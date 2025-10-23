from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import set_language
from django.http import HttpResponse

def health(_):
    return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/setlang/", set_language, name="set_language"),
    path("health/", health, name="health"),
    path("", include("cms.urls", namespace="cms")),
    path("", include("catalog.urls", namespace="catalog")),
    path("", include("cart.urls", namespace="cart")),
    path("", include("orders.urls", namespace="orders")),
    path("", include("payments.urls", namespace="payments")),
    path("", include("users.urls", namespace="users")),
    path("accounts/", include("django.contrib.auth.urls")),
]


# В DEBUG static для приложений (включая admin) раздаются автоматически runserver'ом.
# Подключаем вручную ТОЛЬКО медиа.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
