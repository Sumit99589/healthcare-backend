from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeAdminForm, UserCreationAdminForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    ordering = ["email"]
    list_display = ["email", "name", "is_staff", "is_active", "date_joined"]
    search_fields = ["email", "name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "usable_password", "password1", "password2"),
            },
        ),
    )
