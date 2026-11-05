import calendar
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, TemplateView, UpdateView

from apps.accounts.models import Role
from apps.requests.models import HQRequest

from .forms import EventForm
from .models import Event

MONTH_NAMES_RU = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


class HQStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Доступ разрешен только комсоставу штаба (администраторам и владельцу)."""

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(user.is_hq_staff or user.role in {Role.OWNER, Role.ADMIN})

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("Добавлять и редактировать события календаря может только штаб."))


def serialize_event(evt: Event) -> dict:
    """Унифицированная структура события календаря."""
    return {
        "id": evt.pk,
        "is_request": False,
        "title": evt.title,
        "category_name": evt.get_category_display(),
        "category_code": evt.category,
        "badge_text": evt.get_category_display(),
        "organizer": evt.organizer,
        "event_date": evt.event_date,
        "start_time": evt.start_time,
        "end_time": evt.end_time,
        "location": evt.location,
        "description": evt.description,
        "image": evt.image,
        "url": evt.get_absolute_url(),
        "external_url": evt.url,
        "color_class": "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100",
        "dot_color": "bg-emerald-500",
    }


def serialize_request(req: HQRequest) -> dict:
    """Унифицированная структура штабного запроса для календаря."""
    return {
        "id": req.pk,
        "is_request": True,
        "title": req.title,
        "category_name": f"Запрос ({req.get_level_display()})",
        "category_code": "request",
        "badge_text": f"📢 {req.get_level_display()}",
        "organizer": req.customer,
        "event_date": req.event_date,
        "start_time": req.event_time,
        "end_time": None,
        "location": req.location,
        "description": req.description,
        "image": req.image,
        "url": req.get_absolute_url(),
        "external_url": req.dobro_ru_url,
        "dobro_ru_url": req.dobro_ru_url,
        "responses_count": req.responses.count(),
        "status": req.status,
        "color_class": "bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100",
        "dot_color": "bg-blue-600",
    }


class CalendarView(TemplateView):
    """
    Основная страница календаря событий ШСО ДВФУ.
    Отображает как события штаба (Event), так и запросы (HQRequest)
    в виде интерактивной сетки месяца и хронологического списка.
    """

    template_name = "events/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        # Определение года и месяца
        try:
            year = int(self.request.GET.get("year", today.year))
            month = int(self.request.GET.get("month", today.month))
            if not (1 <= month <= 12):
                raise ValueError
        except (ValueError, TypeError):
            year, month = today.year, today.month

        # Навигация: предыдущий и следующий месяц
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        # Фильтры
        filter_type = self.request.GET.get("type", "all").strip()
        search_query = self.request.GET.get("q", "").strip()
        view_mode = self.request.GET.get("view", "month").strip()
        if view_mode not in {"month", "list"}:
            view_mode = "month"

        # Загрузка событий календаря за выбранный месяц
        events_qs = Event.objects.filter(event_date__year=year, event_date__month=month)
        # Загрузка штабных запросов за выбранный месяц (автоматическое попадание)
        requests_qs = HQRequest.objects.filter(event_date__year=year, event_date__month=month)

        if search_query:
            events_qs = events_qs.filter(
                models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
                | models.Q(location__icontains=search_query)
                | models.Q(organizer__icontains=search_query)
            )
            requests_qs = requests_qs.filter(
                models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
                | models.Q(location__icontains=search_query)
                | models.Q(customer__icontains=search_query)
            )

        items = []
        if filter_type in {"all", "events"}:
            items.extend([serialize_event(e) for e in events_qs])
        if filter_type in {"all", "requests"}:
            items.extend([serialize_request(r) for r in requests_qs])

        # Сортировка всех элементов хронологически
        items.sort(
            key=lambda x: (
                x["event_date"],
                x["start_time"] or time(0, 0),
                x["title"],
            )
        )

        # Группировка элементов по датам (для сетки и списка)
        items_by_date = defaultdict(list)
        for item in items:
            items_by_date[item["event_date"]].append(item)

        # Построение календарной сетки (Пн-Вс)
        cal = calendar.Calendar(firstweekday=0)
        month_weeks = cal.monthdatescalendar(year, month)

        calendar_grid = []
        for week in month_weeks:
            week_days = []
            for day_date in week:
                day_items = items_by_date.get(day_date, [])
                week_days.append(
                    {
                        "date": day_date,
                        "day": day_date.day,
                        "is_current_month": day_date.month == month,
                        "is_today": day_date == today,
                        "items": day_items,
                    }
                )
            calendar_grid.append(week_days)

        # Список дат с событиями (для режима "Список")
        agenda_list = []
        for d in sorted(items_by_date.keys()):
            agenda_list.append({"date": d, "items": items_by_date[d]})

        user = self.request.user
        can_add = bool(
            user.is_authenticated and (user.is_hq_staff or user.role in {Role.OWNER, Role.ADMIN})
        )

        context.update(
            {
                "year": year,
                "month": month,
                "month_name": MONTH_NAMES_RU[month],
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "today": today,
                "weekday_names": WEEKDAY_NAMES_RU,
                "calendar_grid": calendar_grid,
                "agenda_list": agenda_list,
                "filter_type": filter_type,
                "search_query": search_query,
                "view_mode": view_mode,
                "total_items_count": len(items),
                "events_count": events_qs.count(),
                "requests_count": requests_qs.count(),
                "can_add_event": can_add,
            }
        )
        return context


class EventDetailView(DetailView):
    """Детальная страница события календаря."""

    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_manage"] = bool(
            user.is_authenticated and (user.is_hq_staff or user.role in {Role.OWNER, Role.ADMIN})
        )
        return context


class EventCreateView(HQStaffRequiredMixin, CreateView):
    """Создание события в календаре комсоставом штаба."""

    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _(f"Событие «{self.object.title}» успешно добавлено!"))
        return response


class EventUpdateView(HQStaffRequiredMixin, UpdateView):
    """Редактирование события в календаре."""

    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _(f"Событие «{self.object.title}» обновлено!"))
        return response


class EventDeleteView(HQStaffRequiredMixin, DeleteView):
    """Удаление события из календаря."""

    model = Event
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy("events:calendar")

    def form_valid(self, form):
        title = self.object.title
        response = super().form_valid(form)
        messages.success(self.request, _(f"Событие «{title}» удалено из календаря."))
        return response


class EventICalExportView(View):
    """Экспорт события в формат iCalendar (.ics) для добавления в личный календарь."""

    def get(self, request, pk):
        item_type = request.GET.get("type", "event")
        if item_type == "request":
            req = get_object_or_404(HQRequest, pk=pk)
            title = req.title
            desc = req.description or ""
            loc = req.location or ""
            dt_date = req.event_date
            dt_time = req.event_time or time(10, 0)
        else:
            evt = get_object_or_404(Event, pk=pk)
            title = evt.title
            desc = evt.description or ""
            loc = evt.location or ""
            dt_date = evt.event_date
            dt_time = evt.start_time or time(10, 0)

        dt_start = datetime.combine(dt_date, dt_time)
        dt_end = dt_start + timedelta(hours=2)

        start_str = dt_start.strftime("%Y%m%dT%H%M%S")
        end_str = dt_end.strftime("%Y%m%dT%H%M%S")
        now_str = timezone.now().strftime("%Y%m%dT%H%M%SZ")

        clean_title = title.replace("\n", " ").replace("\r", "")
        clean_desc = desc.replace("\r", "").replace("\n", "\\n")
        clean_loc = loc.replace("\n", " ").replace("\r", "")

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//SHSO FEFU//Event Calendar//RU\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:shso-event-{pk}-{dt_start.strftime('%Y%m%d')}@fefu.ru\r\n"
            f"DTSTAMP:{now_str}\r\n"
            f"DTSTART:{start_str}\r\n"
            f"DTEND:{end_str}\r\n"
            f"SUMMARY:{clean_title}\r\n"
            f"DESCRIPTION:{clean_desc}\r\n"
            f"LOCATION:{clean_loc}\r\n"
            "STATUS:CONFIRMED\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
        filename = f"event_{pk}.ics"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
