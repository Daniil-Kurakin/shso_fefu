from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    FAQCategory,
    FAQItem,
    GlossaryTerm,
    KnowledgeArticle,
    KnowledgeCategory,
    Quote,
    SiteSetting,
    StaffMember,
)


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


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "title", "slug", "articles_count_display", "order")
    list_editable = ("order",)
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "title")

    @admin.display(description=_("Статей"))
    def articles_count_display(self, obj):
        return obj.articles.count()


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "pinned",
        "is_published",
        "views_count",
        "order",
        "created_at",
    )
    list_filter = ("category", "pinned", "is_published")
    search_fields = ("title", "summary", "content")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("pinned", "is_published", "order")
    ordering = ("-pinned", "order", "-created_at")


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "items_count_display", "order")
    list_editable = ("order",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "title")

    @admin.display(description=_("Вопросов"))
    def items_count_display(self, obj):
        return obj.items.count()


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_published", "order", "created_at")
    list_filter = ("category", "is_published")
    search_fields = ("question", "answer")
    list_editable = ("is_published", "order")
    ordering = ("order", "id")


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ("term", "letter", "synonyms", "order")
    list_filter = ("letter",)
    search_fields = ("term", "definition", "synonyms")
    prepopulated_fields = {"slug": ("term",)}
    list_editable = ("order",)
    ordering = ("letter", "term")
