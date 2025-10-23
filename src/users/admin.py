from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Shop fields", {"fields": ("phone", "receive_marketing")}),
    )
    list_display = ("username", "email", "phone", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "phone")
