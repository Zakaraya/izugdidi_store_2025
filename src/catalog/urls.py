from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("catalog/", views.product_list, name="product_list"),
    path("catalog/<slug:category_slug>/", views.product_list, name="product_list_by_category"),
    path("p/<slug:base_slug>/", views.product_detail, name="product_detail"),
    path("favorite/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("favorites/", views.favorite_list, name="favorites"),
]
