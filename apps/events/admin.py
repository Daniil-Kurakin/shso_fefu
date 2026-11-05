from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "organizer",
        "event_date",
        "start_time",
        "end_time",
        "location",
        "created_at",
    )
    list_filter = ("category", "event_date")
    search_fields = ("title", "description", "organizer", "location")
    raw_id_fields = ("created_by",)
    date_hierarchy = "event_date"
