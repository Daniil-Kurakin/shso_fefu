from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "role",
        "email_verified",
        "is_active",
        "consent_personal_data",
    )
    list_filter = ("role", "email_verified", "is_active", "is_staff", "consent_personal_data")
    search_fields = ("email", "full_name", "phone")
    readonly_fields = ("consent_date", "consent_ip")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Личные данные"), {"fields": ("full_name", "phone", "signature", "language")}),
        (
            _("Права и статус"),
            {
                "fields": (
                    "role",
                    "email_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("152-ФЗ и аудит согласий"),
            {
                "fields": (
                    "consent_personal_data",
                    "consent_date",
                    "consent_ip",
                )
            },
        ),
        (_("Даты"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
