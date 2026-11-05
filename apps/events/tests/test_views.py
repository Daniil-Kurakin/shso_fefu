from datetime import date, time

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.events.models import Event
from apps.requests.models import HQRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return User.objects.create_user("admin_cal@example.com", "pass123", role=Role.ADMIN)


@pytest.fixture
def regular_user():
    return User.objects.create_user("fighter_cal@example.com", "pass123", role=Role.MEMBER)


@pytest.fixture
def test_event(admin_user):
    return Event.objects.create(
        title="Школа комсостава 2026",
        category=Event.Category.SCHOOL,
        organizer="ШСО ДВФУ",
        event_date=date(2026, 11, 15),
        start_time=time(11, 0),
        end_time=time(17, 0),
        location="Синий зал",
        description="Интенсив по лидерству и управлению отрядом.",
        created_by=admin_user,
    )


@pytest.fixture
def test_request(admin_user):
    return HQRequest.objects.create(
        title="Волонтерство на Конгрессе",
        description="Помощь на международном конгрессе.",
        customer="Ректорат ДВФУ",
        level=HQRequest.Level.ALL_RUSSIAN,
        event_date=date(2026, 11, 15),
        event_time=time(9, 30),
        location="Корпус В",
        status=HQRequest.Status.OPEN,
        created_by=admin_user,
    )


class TestCalendarView:
    def test_calendar_displays_both_events_and_hq_requests(self, client, test_event, test_request):
        url = reverse("events:calendar") + "?year=2026&month=11"
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")

        # Оба события автоматически отображаются в календаре
        assert "Школа комсостава 2026" in content
        assert "Волонтерство на Конгрессе" in content

    def test_calendar_filters(self, client, test_event, test_request):
        # Только события
        url_events = reverse("events:calendar") + "?year=2026&month=11&type=events"
        resp_events = client.get(url_events)
        assert resp_events.status_code == 200
        c_events = resp_events.content.decode("utf-8")
        assert "Школа комсостава 2026" in c_events
        assert "Волонтерство на Конгрессе" not in c_events

        # Только штабные запросы
        url_requests = reverse("events:calendar") + "?year=2026&month=11&type=requests"
        resp_requests = client.get(url_requests)
        assert resp_requests.status_code == 200
        c_requests = resp_requests.content.decode("utf-8")
        assert "Волонтерство на Конгрессе" in c_requests
        assert "Школа комсостава 2026" not in c_requests

    def test_calendar_list_view_mode(self, client, test_event, test_request):
        url = reverse("events:calendar") + "?year=2026&month=11&view=list"
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Школа комсостава 2026" in content
        assert "Волонтерство на Конгрессе" in content

    def test_calendar_search(self, client, test_event, test_request):
        url = reverse("events:calendar") + "?year=2026&month=11&q=Интенсив"
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Школа комсостава 2026" in content
        assert "Волонтерство на Конгрессе" not in content


class TestEventDetailView:
    def test_event_detail_renders(self, client, test_event):
        url = reverse("events:detail", kwargs={"pk": test_event.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Школа комсостава 2026" in content
        assert "Синий зал" in content
        assert "ШСО ДВФУ" in content


class TestEventPermissions:
    def test_regular_user_cannot_create_event(self, client, regular_user):
        client.force_login(regular_user)
        url = reverse("events:create")
        resp = client.get(url)
        assert resp.status_code == 403

    def test_admin_can_create_event(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("events:create")
        resp = client.get(url)
        assert resp.status_code == 200

        data = {
            "title": "Слёт студенческих отрядов",
            "category": Event.Category.GENERAL,
            "organizer": "ШСО ДВФУ",
            "event_date": "2026-11-25",
            "start_time": "14:00",
            "end_time": "18:00",
            "location": "Корпус В, Аякс",
            "description": "Итоговый слёт отрядов за год.",
            "url": "https://vk.com/shso_fefu",
        }
        post_resp = client.post(url, data)
        assert post_resp.status_code == 302
        new_event = Event.objects.get(title="Слёт студенческих отрядов")
        assert new_event.location == "Корпус В, Аякс"
        assert new_event.created_by == admin_user

    def test_admin_can_update_and_delete_event(self, client, admin_user, test_event):
        client.force_login(admin_user)

        # Update
        edit_url = reverse("events:edit", kwargs={"pk": test_event.pk})
        client.post(
            edit_url,
            {
                "title": "Обновленная школа комсостава",
                "category": test_event.category,
                "organizer": test_event.organizer,
                "event_date": test_event.event_date.strftime("%Y-%m-%d"),
                "location": test_event.location,
            },
        )
        test_event.refresh_from_db()
        assert test_event.title == "Обновленная школа комсостава"

        # Delete
        del_url = reverse("events:delete", kwargs={"pk": test_event.pk})
        del_resp = client.post(del_url)
        assert del_resp.status_code == 302
        assert not Event.objects.filter(pk=test_event.pk).exists()


class TestEventICalExport:
    def test_export_event_ics(self, client, test_event):
        url = reverse("events:export_ics", kwargs={"pk": test_event.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert "text/calendar" in resp["Content-Type"]
        content = resp.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "SUMMARY:Школа комсостава 2026" in content
        assert "END:VCALENDAR" in content

    def test_export_request_ics(self, client, test_request):
        url = reverse("events:export_ics", kwargs={"pk": test_request.pk}) + "?type=request"
        resp = client.get(url)
        assert resp.status_code == 200
        assert "text/calendar" in resp["Content-Type"]
        content = resp.content.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "SUMMARY:Волонтерство на Конгрессе" in content
