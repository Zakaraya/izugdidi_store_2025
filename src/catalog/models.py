from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from django.conf import settings

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Category(TranslatableModel, TimeStamped):
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    slug = models.SlugField(unique=True, max_length=140)
    translations = TranslatedFields(
        name=models.CharField(max_length=140),
        description=models.TextField(blank=True),
    )
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["slug"]
    def __str__(self):
        return self.safe_translation_getter('name', any_language=True) or self.slug

class Brand(TimeStamped):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True, max_length=140)
    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ["name"]
    def __str__(self):
        return self.name

class Product(TranslatableModel, TimeStamped):
    class Condition(models.TextChoices):
        A = "A", _("Excellent")
        B = "B", _("Good")
        C = "C", _("Fair")

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    model_name = models.CharField(max_length=140)
    base_slug = models.SlugField(unique=True, max_length=160)
    condition = models.CharField(max_length=1, choices=Condition.choices, default=Condition.A)
    battery_health_percent = models.PositiveSmallIntegerField(default=100)
    storage_gb = models.PositiveSmallIntegerField()
    color = models.CharField(max_length=60)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="GEL")
    in_stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=64, unique=True)
    imei_hash = models.CharField(max_length=64, blank=True)
    warranty_months = models.PositiveSmallIntegerField(default=1)
    is_published = models.BooleanField(default=True)

    translations = TranslatedFields(
        title=models.CharField(max_length=160),
        description=models.TextField(blank=True),
    )

    class Meta:
        indexes = [
            models.Index(fields=["category", "price"]),
            models.Index(fields=["condition", "storage_gb"]),
        ]
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand.name} {self.model_name} {self.storage_gb}GB {self.color}"

class ProductImage(TimeStamped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    file = models.ImageField(upload_to="products/%Y/%m/")
    alt = models.CharField(max_length=160, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = _("Product image")
        verbose_name_plural = _("Product images")
        constraints = [
            models.UniqueConstraint(fields=["product", "position"], name="uniq_product_pos"),
            models.CheckConstraint(check=models.Q(position__gte=0) & models.Q(position__lte=9),
                                   name="position_between_0_and_9"),
        ]

    def __str__(self):
        return f"Image for {self.product_id}"

    def clean(self):
        # ограничим максимум 10 фото на продукт
        if self.product_id:
            qs = ProductImage.objects.filter(product_id=self.product_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= 10:
                from django.core.exceptions import ValidationError
                raise ValidationError(_("Maximum 10 images per product."))


class Favorite(TimeStamped):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_favorite', condition=models.Q(user__isnull=False)),
            models.UniqueConstraint(fields=['session_key', 'product'], name='unique_session_favorite', condition=models.Q(session_key__isnull=False)),
        ]