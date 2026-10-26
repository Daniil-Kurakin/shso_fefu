from datetime import time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.requests.models import CampusPremise, PassRequest, PassVisitor, RoomBookingRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        "user1@example.com", "pass-12345", full_name="Алексей Заявитель"
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        "user2@example.com", "pass-12345", full_name="Другой Пользователь"
    )


@pytest.fixture
def room():
    return CampusPremise.objects.create(
        name="«Синий зал»",
        building=CampusPremise.Building.CORPUS_A,
        capacity=100,
    )


class TestDashboardView:
    def test_dashboard_guest_redirects(self, client):
        url = reverse("requests:dashboard")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_dashboard_authenticated(self, client, user, room):
        client.force_login(user)
        tomorrow = timezone.localdate() + timedelta(days=1)
        RoomBookingRequest.objects.create(
            user=user,
            room=room,
            event_name="Моя встреча",
            event_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )

        url = reverse("requests:dashboard")
        response = client.get(url)
        assert response.status_code == 200
        assert "Моя встреча".encode() in response.content


class TestRoomBookingViews:
    def test_create_booking_success(self, client, user, room):
        client.force_login(user)
        tomorrow = timezone.localdate() + timedelta(days=2)
        url = reverse("requests:room_create")

        data = {
            "room": room.id,
            "event_name": "Репетиция гимна ШСО",
            "event_date": tomorrow.strftime("%Y-%m-%d"),
            "start_time": "18:00",
            "end_time": "20:00",
            "expected_participants": 25,
            "equipment_required": "Микрофоны",
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200

        booking = RoomBookingRequest.objects.get(event_name="Репетиция гимна ШСО")
        assert booking.user == user
        assert booking.status == RoomBookingRequest.Status.SUBMITTED

    def test_create_booking_collision_error(self, client, user, room):
        tomorrow = timezone.localdate() + timedelta(days=2)
        # Уже одобренная бронь
        RoomBookingRequest.objects.create(
            user=user,
            room=room,
            event_name="Занято",
            event_date=tomorrow,
            start_time=time(18, 0),
            end_time=time(20, 0),
            status=RoomBookingRequest.Status.APPROVED,
        )

        client.force_login(user)
        url = reverse("requests:room_create")
        data = {
            "room": room.id,
            "event_name": "Вторая бронь в то же время",
            "event_date": tomorrow.strftime("%Y-%m-%d"),
            "start_time": "18:30",
            "end_time": "19:30",
            "expected_participants": 10,
        }
        response = client.post(url, data=data)
        assert response.status_code == 200
        assert "уже занято на это время".encode() in response.content
        assert not RoomBookingRequest.objects.filter(
            event_name="Вторая бронь в то же время"
        ).exists()

    def test_detail_view_permissions(self, client, user, other_user, room):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = RoomBookingRequest.objects.create(
            user=user,
            room=room,
            event_name="Закрытая встреча",
            event_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        # Заявитель видит 200
        client.force_login(user)
        res_owner = client.get(booking.get_absolute_url())
        assert res_owner.status_code == 200

        # Посторонний получает 403
        client.force_login(other_user)
        res_other = client.get(booking.get_absolute_url())
        assert res_other.status_code == 403

    def test_cancel_booking(self, client, user, other_user, room):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = RoomBookingRequest.objects.create(
            user=user,
            room=room,
            event_name="Встреча на отмену",
            event_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        url = reverse("requests:room_cancel", kwargs={"pk": booking.pk})

        # Посторонний не может отменить
        client.force_login(other_user)
        res_forbidden = client.post(url)
        assert res_forbidden.status_code == 403

        # Заявитель отменяет успешно
        client.force_login(user)
        res_cancel = client.post(url, follow=True)
        assert res_cancel.status_code == 200
        booking.refresh_from_db()
        assert booking.status == RoomBookingRequest.Status.CANCELLED


class TestPassRequestViews:
    def test_create_pass_with_visitors(self, client, user):
        client.force_login(user)
        visit_d = timezone.localdate() + timedelta(days=5)
        url = reverse("requests:pass_create")

        data = {
            "title": "Гости на фестиваль",
            "pass_type": PassRequest.PassType.GROUP,
            "visit_date": visit_d.strftime("%Y-%m-%d"),
            "entry_point": "Северные ворота",
            "data_consent": True,
            # Management form для visitors formset
            "visitors-TOTAL_FORMS": "2",
            "visitors-INITIAL_FORMS": "0",
            "visitors-MIN_NUM_FORMS": "0",
            "visitors-MAX_NUM_FORMS": "1000",
            # Первый посетитель
            "visitors-0-full_name": "Иванов Иван",
            "visitors-0-document_type": PassVisitor.DocumentType.PASSPORT,
            "visitors-0-document_data": "0515 111222",
            "visitors-0-organization": "ДВФУ",
            "visitors-0-phone": "+79990001122",
            # Второй посетитель
            "visitors-1-full_name": "Петров Петр",
            "visitors-1-document_type": PassVisitor.DocumentType.STUDENT_ID,
            "visitors-1-document_data": "СТ-12345",
            "visitors-1-organization": "ВГУЭС",
            "visitors-1-phone": "+79990003344",
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200

        pr = PassRequest.objects.get(title="Гости на фестиваль")
        assert pr.user == user
        assert pr.status == PassRequest.Status.SUBMITTED
        assert pr.visitors.count() == 2

    def test_detail_view_and_cancel_pass(self, client, user, other_user):
        visit_d = timezone.localdate() + timedelta(days=3)
        pr = PassRequest.objects.create(
            user=user,
            title="Пропуск на слёт",
            pass_type=PassRequest.PassType.INDIVIDUAL,
            visit_date=visit_d,
        )

        client.force_login(user)
        res = client.get(pr.get_absolute_url())
        assert res.status_code == 200

        # Отмена
        cancel_url = reverse("requests:pass_cancel", kwargs={"pk": pr.pk})
        client.post(cancel_url, follow=True)
        pr.refresh_from_db()
        assert pr.status == PassRequest.Status.CANCELLED
