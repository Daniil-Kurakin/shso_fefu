import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Vacancy, VacancyApplication


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "squad",
        "salary",
        "slots_count",
        "deadline",
        "status",
        "applications_count_display",
        "created_at",
    )
    list_filter = ("status", "type", "squad", "deadline")
    search_fields = ("title", "description", "requirements")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)
    actions = ["action_open", "action_close"]

    @admin.display(description=_("Откликов"))
    def applications_count_display(self, obj):
        return obj.applications_count

    @admin.action(description=_("Открыть выбранные вакансии для откликов"))
    def action_open(self, request, queryset):
        count = queryset.update(status=Vacancy.Status.OPEN)
        self.message_user(request, _(f"Открыто вакансий: {count}"))

    @admin.action(description=_("Закрыть выбранные вакансии"))
    def action_close(self, request, queryset):
        count = queryset.update(status=Vacancy.Status.CLOSED)
        self.message_user(request, _(f"Закрыто вакансий: {count}"))


@admin.register(VacancyApplication)
class VacancyApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "applicant_name",
        "vacancy",
        "contact_type",
        "contact_value",
        "user",
        "status",
        "assigned_squad",
        "created_at",
    )
    list_filter = (
        "status",
        "vacancy__type",
        "vacancy",
        "contact_type",
        "assigned_squad",
        "created_at",
    )
    search_fields = ("applicant_name", "contact_value", "internal_comment")
    ordering = ("-created_at",)
    actions = [
        "export_as_csv",
        "action_mark_contacted",
        "action_mark_accepted",
        "action_mark_rejected",
    ]

    @admin.action(description=_("Экспортировать выбранные отклики в CSV (Excel)"))
    def export_as_csv(self, request, queryset):
        """Выгрузка откликов в CSV с кодировкой UTF-8 BOM для корректного открытия в Excel."""
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        now_str = timezone.now().strftime("%Y%m%d_%H%M")
        response["Content-Disposition"] = f'attachment; filename="applications_{now_str}.csv"'

        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "ID",
                "ФИО соискателя",
                "Вакансия",
                "Тип контакта",
                "Контакт",
                "Пользователь сайта",
                "Статус",
                "Назначенный отряд",
                "Дата подачи",
                "Внутренний комментарий",
            ]
        )

        for app in queryset.select_related("vacancy", "user", "assigned_squad"):
            writer.writerow(
                [
                    app.pk,
                    app.applicant_name,
                    app.vacancy.title,
                    app.get_contact_type_display(),
                    app.contact_value,
                    app.user.email if app.user else "—",
                    app.get_status_display(),
                    app.assigned_squad.name if app.assigned_squad else "—",
                    app.created_at.strftime("%d.%m.%Y %H:%M"),
                    app.internal_comment,
                ]
            )

        return response

    @admin.action(description=_("Отметить статус: Связались"))
    def action_mark_contacted(self, request, queryset):
        count = queryset.update(status=VacancyApplication.Status.CONTACTED)
        self.message_user(request, _(f"Обновлено откликов: {count}"))

    @admin.action(description=_("Отметить статус: Принят"))
    def action_mark_accepted(self, request, queryset):
        count = queryset.update(status=VacancyApplication.Status.ACCEPTED)
        self.message_user(request, _(f"Принято соискателей: {count}"))

    @admin.action(description=_("Отметить статус: Отказ"))
    def action_mark_rejected(self, request, queryset):
        count = queryset.update(status=VacancyApplication.Status.REJECTED)
        self.message_user(request, _(f"Отклонено откликов: {count}"))
