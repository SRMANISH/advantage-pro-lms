from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "full_name", "role", "status", "email", "is_active")
    list_filter = ("role", "status", "is_active")
    search_fields = ("username", "full_name", "email", "phone")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profile", {"fields": ("full_name", "email", "phone")}),
        ("Role & status", {"fields": ("role", "status")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("date_joined", "last_login")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "full_name", "email", "role", "password1", "password2"),
            },
        ),
    )

    # Closed here specifically: there is no user-deletion endpoint, so this was the only way
    # to remove an account — and it cascades to attendance, submissions, attempts and video
    # progress with no warning. Suspension (UserStatusView) is the reversible operation staff
    # actually want. A genuine erasure request should be a deliberate, logged operation with
    # the cascade understood, not two clicks in a list view.
    def has_delete_permission(self, request, obj=None):
        return False
