import csv

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import CampusPremise, PassRequest, PassVisitor, RoomBookingRequest


class PassVisitorInline(admin.TabularInline):
    model = PassVisitor
    extra = 0
    fields = ("full_name", "document_type", "document_data", "organization", "phone")


@admin.register(CampusPremise)
class CampusPremiseAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "room_number", "capacity", "is_active", "order")
    list_filter = ("building", "is_active")
    search_fields = ("name", "room_number", "equipment_description")
    list_editable = ("is_active", "order")
    ordering = ("building", "order", "name")


@admin.register(RoomBookingRequest)
class RoomBookingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "room",
        "event_date",
        "time_interval",
        "user",
        "squad",
        "status",
        "collision_status",
        "created_at",
    )
    list_filter = ("status", "room__building", "room", "event_date")
    search_fields = ("event_name", "user__email", "user__full_name", "moderator_comment")
    raw_id_fields = ("user", "reviewed_by")
    ordering = ("-event_date", "-start_time")
    actions = ["action_approve", "action_reject"]

    @admin.display(description=_("Время"))
    def time_interval(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} – {obj.end_time.strftime('%H:%M')}"

    @admin.display(description=_("Коллизии / Доступность"))
    def collision_status(self, obj):
        if obj.status == RoomBookingRequest.Status.APPROVED:
            return mark_safe('<span style="color: green; font-weight: bold;">✓ Одобрена</span>')

        conflicts = obj.get_conflicting_bookings()
        if not conflicts.exists():
            return mark_safe('<span style="color: gray;">Свободно</span>')

        approved_conflict = conflicts.filter(status=RoomBookingRequest.Status.APPROVED).first()
        if approved_conflict:
            return format_html(
                '<span style="color: red; font-weight: bold;" '
                'title="Пересекается с: {}">⚠️ Конфликт с одобренной!</span>',
                approved_conflict.event_name,
            )

        return format_html(
            '<span style="color: #b45309;" '
            'title="Пересекается с {} заявкой(-ами)">⚡ Пересечение заявок ({})</span>',
            conflicts.count(),
            conflicts.count(),
        )

    @admin.action(description=_("Одобрить выбранные бронирования"))
    def action_approve(self, request, queryset):
        success = 0
        failed = 0
        for booking in queryset:
            try:
                booking.approve(moderator=request.user)
                success += 1
            except ValidationError as e:
                failed += 1
                self.message_user(
                    request,
                    _(f"Не удалось одобрить «{booking.event_name}»: {e}"),
                    level="error",
                )
        if success:
            self.message_user(request, _(f"Одобрено заявок на помещения: {success}"))

    @admin.action(description=_("Отклонить выбранные бронирования"))
    def action_reject(self, request, queryset):
        for booking in queryset:
            booking.reject(moderator=request.user)
        self.message_user(request, _(f"Отклонено заявок: {queryset.count()}"))


@admin.register(PassRequest)
class PassRequestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "pass_type",
        "visit_interval",
        "user",
        "squad",
        "visitors_count_display",
        "status",
        "is_data_purged",
        "created_at",
    )
    list_filter = ("status", "pass_type", "visit_date", "is_data_purged")
    search_fields = (
        "title",
        "user__email",
        "user__full_name",
        "car_number",
        "entry_point",
        "moderator_comment",
    )
    raw_id_fields = ("user", "reviewed_by")
    inlines = [PassVisitorInline]
    ordering = ("-visit_date", "-created_at")
    actions = [
        "export_pass_list_csv",
        "action_approve",
        "action_reject",
        "action_purge_data",
    ]

    @admin.display(description=_("Даты визита"))
    def visit_interval(self, obj):
        if obj.visit_end_date and obj.visit_end_date != obj.visit_date:
            return (
                f"{obj.visit_date.strftime('%d.%m.%Y')} – {obj.visit_end_date.strftime('%d.%m.%Y')}"
            )
        return obj.visit_date.strftime("%d.%m.%Y")

    @admin.display(description=_("Гостей"))
    def visitors_count_display(self, obj):
        return obj.visitors.count()

    @admin.action(description=_("Выгрузить список в Excel/CSV для бюро пропусков"))
    def export_pass_list_csv(self, request, queryset):
        """Выгрузка списка персон на пропуска в кодировке UTF-8 BOM для бюро пропусков ДВФУ."""
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        now_str = timezone.now().strftime("%Y%m%d_%H%M")
        response["Content-Disposition"] = f'attachment; filename="pass_visitors_{now_str}.csv"'

        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "Заявка ID",
                "Мероприятие / Цель",
                "Дата с",
                "Дата по",
                "КПП",
                "Автомобиль",
                "Госномер",
                "ФИО посетителя",
                "Тип документа",
                "Серия и номер документа",
                "Организация",
                "Телефон",
                "Заявитель",
                "Отряд",
            ]
        )

        for pr in queryset.prefetch_related("visitors").select_related("user", "squad"):
            car_info = pr.car_model or "—"
            car_num = pr.car_number or "—"
            end_d = pr.visit_end_date.strftime("%d.%m.%Y") if pr.visit_end_date else "—"
            squad_name = pr.squad.name if pr.squad else "—"

            for v in pr.visitors.all():
                writer.writerow(
                    [
                        pr.pk,
                        pr.title,
                        pr.visit_date.strftime("%d.%m.%Y"),
                        end_d,
                        pr.entry_point,
                        car_info,
                        car_num,
                        v.full_name,
                        v.get_document_type_display(),
                        v.document_data,
                        v.organization or "—",
                        v.phone or "—",
                        pr.user.get_full_name(),
                        squad_name,
                    ]
                )

        return response

    @admin.action(description=_("Одобрить выбранные пропуска"))
    def action_approve(self, request, queryset):
        for pr in queryset:
            pr.approve(moderator=request.user)
        self.message_user(request, _(f"Одобрено заявок на пропуска: {queryset.count()}"))

    @admin.action(description=_("Отклонить выбранные пропуска"))
    def action_reject(self, request, queryset):
        for pr in queryset:
            pr.reject(moderator=request.user)
        self.message_user(request, _(f"Отклонено заявок на пропуска: {queryset.count()}"))

    @admin.action(description=_("Очистить персональные данные (152-ФЗ)"))
    def action_purge_data(self, request, queryset):
        count = 0
        for pr in queryset:
            pr.purge_personal_data()
            count += 1
        self.message_user(request, _(f"Персональные данные очищены для {count} заявок."))
