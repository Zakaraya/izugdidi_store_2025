from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from parler.admin import TranslatableAdmin
from .models import Category, Brand, Product, ProductImage

@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    list_display = ("slug", "translated_name", "parent")
    search_fields = ("translations__name", "slug")
    list_filter = ("parent",)
    def translated_name(self, obj):
        return obj.safe_translation_getter("name", any_language=True)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")

class ProductImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        count = 0
        positions = set()
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data.get("file"):
                continue
            count += 1
            pos = form.cleaned_data.get("position", 0)
            if pos in positions:
                raise forms.ValidationError("Positions must be unique per product.")
            positions.add(pos)
        if count < 1:
            raise forms.ValidationError("At least one image is required.")
        if count > 10:
            raise forms.ValidationError("No more than 10 images allowed.")

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    min_num = 1
    max_num = 10
    formset = ProductImageInlineFormSet

@admin.register(Product)
class ProductAdmin(TranslatableAdmin):
    list_display = ("title_any", "brand", "model_name", "storage_gb", "color", "condition", "price", "in_stock", "is_published")
    list_filter = ("brand", "category", "condition", "storage_gb", "color", "is_published")
    search_fields = ("translations__title", "model_name", "sku", "base_slug")
    inlines = [ProductImageInline]
    prepopulated_fields = {"base_slug": ("model_name",)}
    def title_any(self, obj):
        return obj.safe_translation_getter("title", any_language=True)
    title_any.short_description = "Title"
