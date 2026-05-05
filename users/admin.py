from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "role",
        "isEmailVerified",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "isEmailVerified",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "JobMatch information",
            {
                "fields": (
                    "role",
                    "isEmailVerified",
                    "createdAt",
                )
            },
        ),
    )

    readonly_fields = ("createdAt",)