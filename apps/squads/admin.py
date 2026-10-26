from django.contrib import admin

from .models import Direction, Squad


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order", "squads_count")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")

    @admin.display(description="Отрядов")
    def squads_count(self, obj):
        return obj.squads.count()


@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ("name", "direction", "founding_year", "is_recruiting", "created_at")
    list_filter = ("direction", "is_recruiting", "founding_year")
    search_fields = ("name", "motto", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
