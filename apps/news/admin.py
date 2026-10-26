from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import News, NewsImage


class NewsImageInline(admin.TabularInline):
    model = NewsImage
    extra = 1
    fields = ("image", "caption", "order")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "organizer",
        "squad",
        "status",
        "published_at",
        "author",
    )
    list_filter = ("status", "category", "organizer", "squad", "published_at")
    search_fields = ("title", "lead", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    inlines = [NewsImageInline]
    actions = ["action_publish", "action_return_for_revision"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "slug",
                    "category",
                    "organizer",
                    "squad",
                    "cover",
                    "lead",
                    "content",
                    "source_url",
                )
            },
        ),
        (
            _("Модерация и статус"),
            {
                "fields": (
                    "status",
                    "moderator_comment",
                    "published_at",
                    "author",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description=_("Опубликовать выбранные новости"))
    def action_publish(self, request, queryset):
        count = queryset.update(
            status=News.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, _(f"Опубликовано новостей: {count}"))

    @admin.action(description=_("Вернуть на доработку"))
    def action_return_for_revision(self, request, queryset):
        count = queryset.update(status=News.Status.RETURNED)
        self.message_user(request, _(f"Возвращено на доработку: {count}"))
