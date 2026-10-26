from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm
from .models import Role, User, UserPortfolioItem


def owner_only_has_permission(request):
    """Доступ к Django админ-панели разрешён исключительно владельцу сайта."""
    if not request.user.is_active:
        return False
    return bool(request.user.is_superuser or getattr(request.user, "role", None) == Role.OWNER)


admin.site.has_permission = owner_only_has_permission


class UserPortfolioItemInline(admin.TabularInline):
    model = UserPortfolioItem
    extra = 0
    fields = ("title", "category", "year", "organization", "image")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("email",)
    inlines = [UserPortfolioItemInline]
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
        (
            _("Личные данные"),
            {
                "fields": (
                    "full_name",
                    "avatar",
                    "phone",
                    "telegram",
                    "vk_url",
                    "bio",
                    "signature",
                    "language",
                )
            },
        ),
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


@admin.register(UserPortfolioItem)
class UserPortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "year", "organization", "created_at")
    list_filter = ("category", "year")
    search_fields = ("title", "organization", "user__email", "user__full_name")
    raw_id_fields = ("user",)
