from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from catalog.models import Product

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Coupon(TimeStamped):
    class Type(models.TextChoices):
        PERCENT = "percent", _("Percent")
        FIXED = "fixed", _("Fixed amount")

    code = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    min_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    usage_limit_total = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stackable = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
        indexes = [models.Index(fields=["code"])]

    def __str__(self):
        return self.code

    def is_valid_now(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at

class Order(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PENDING = "pending", _("Pending payment")
        PAID = "paid", _("Paid")
        PROCESSING = "processing", _("Processing")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        RETURNED = "returned", _("Returned")

    DELIVERY_PICKUP = "pickup"
    DELIVERY_ADDRESS = "address"
    DELIVERY_CHOICES = [
        (DELIVERY_PICKUP, "Самовывоз"),
        (DELIVERY_ADDRESS, "Доставка по адресу"),
    ]

    delivery_method = models.CharField(
        max_length=16, choices=DELIVERY_CHOICES, default=DELIVERY_PICKUP
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="GEL")

    email = models.EmailField()
    phone = models.CharField(max_length=40)
    customer_name = models.CharField(max_length=140)

    shipping_address_json = models.JSONField()
    billing_address_json = models.JSONField()

    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    payment_provider = models.CharField(max_length=32, blank=True)
    payment_intent_id = models.CharField(max_length=64, blank=True)
    placed_at = models.DateTimeField(null=True, blank=True)

    tracking_number = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.status}"

class OrderItem(TimeStamped):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    title_snapshot = models.CharField(max_length=200)
    qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def line_total(self):
        return self.unit_price_snapshot * self.qty
