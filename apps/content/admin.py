from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Quote, SiteSetting, StaffMember


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "text_preview",
        "author",
        "author_title",
        "language",
        "is_active",
        "pinned_date",
        "created_at",
    )
    list_filter = ("is_active", "language", "pinned_date")
    search_fields = ("text", "author", "author_title")
    list_editable = ("is_active", "pinned_date")
    date_hierarchy = "pinned_date"

    @admin.display(description=_("Текст"))
    def text_preview(self, obj):
        return obj.text[:60] + ("..." if len(obj.text) > 60 else "")


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "position",
        "responsibility",
        "order",
        "email",
        "phone",
        "is_active",
    )
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "position", "responsibility", "email")
    ordering = ("order", "full_name")


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "year", "source", "description")
    search_fields = ("key", "value", "source", "description")
    ordering = ("key",)
