from django.contrib import admin
from .models import Order, OrderItem, Coupon

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "title_snapshot", "qty", "unit_price_snapshot")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "customer_name", "email", "total", "discount_total", "shipping_total", "currency", "placed_at", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "email", "phone", "customer_name", "tracking_number")
    inlines = [OrderItemInline]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "value", "min_total", "starts_at", "ends_at", "is_active", "usage_limit_total", "usage_limit_per_user", "stackable")
    list_filter = ("type", "is_active")
    search_fields = ("code",)
