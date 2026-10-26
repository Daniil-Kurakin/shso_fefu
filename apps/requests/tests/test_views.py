from datetime import time, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.requests.models import CampusPremise, PassRequest, PassVisitor, RoomBookingRequest
from apps.squads.models import Direction, Squad, SquadPageRevision

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
def admin_user():
    return User.objects.create_user("admin_moderator@example.com", "pass-12345", role=Role.ADMIN)


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

    def test_create_booking_with_multiple_rooms_formset(self, client, user):
        client.force_login(user)
        tomorrow = timezone.localdate() + timedelta(days=2)
        url = reverse("requests:room_create")

        data = {
            "event_name": "Большой слёт с несколькими залами",
            "event_date": tomorrow.strftime("%Y-%m-%d"),
            "expected_participants": 50,
            "equipment_required": "Проекторы и звук",
            "premises-TOTAL_FORMS": "2",
            "premises-INITIAL_FORMS": "0",
            "premises-MIN_NUM_FORMS": "0",
            "premises-MAX_NUM_FORMS": "1000",
            "premises-0-custom_room": "Синий зал",
            "premises-0-start_time": "10:00",
            "premises-0-end_time": "13:00",
            "premises-1-custom_room": "Коворкинг Аякс",
            "premises-1-start_time": "13:30",
            "premises-1-end_time": "16:00",
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200

        booking = RoomBookingRequest.objects.get(event_name="Большой слёт с несколькими залами")
        assert booking.premises.count() == 2
        p1, p2 = list(booking.premises.all())
        assert p1.room_name == "Синий зал"
        assert p2.room_name == "Коворкинг Аякс"

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


class TestAdminModerationView:
    def test_moderation_requires_admin_or_owner(self, client, user):
        client.force_login(user)
        url = reverse("requests:moderation")
        response = client.get(url)
        assert response.status_code == 403

    def test_moderation_renders_for_admin(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("requests:moderation")
        response = client.get(url)
        assert response.status_code == 200

    def test_approve_and_reject_room_booking(self, client, admin_user, user, room):
        client.force_login(admin_user)
        tomorrow = timezone.localdate() + timedelta(days=2)
        booking = RoomBookingRequest.objects.create(
            user=user,
            room=room,
            event_name="Собрание штаба",
            event_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
            status=RoomBookingRequest.Status.SUBMITTED,
        )

        # Одобрение
        url = reverse("requests:moderation")
        res = client.post(
            url,
            {"action": "approve_room", "target_id": booking.pk, "tab": "rooms"},
            follow=True,
        )
        assert res.status_code == 200
        booking.refresh_from_db()
        assert booking.status == RoomBookingRequest.Status.APPROVED
        assert booking.reviewed_by == admin_user

        # Отклонение
        client.post(
            url,
            {
                "action": "reject_room",
                "target_id": booking.pk,
                "comment": "Мест нет",
                "tab": "rooms",
            },
            follow=True,
        )
        booking.refresh_from_db()
        assert booking.status == RoomBookingRequest.Status.REJECTED
        assert booking.moderator_comment == "Мест нет"

    def test_approve_and_reject_pass_request(self, client, admin_user, user):
        client.force_login(admin_user)
        visit_d = timezone.localdate() + timedelta(days=2)
        pr = PassRequest.objects.create(
            user=user,
            title="Гости",
            pass_type=PassRequest.PassType.INDIVIDUAL,
            visit_date=visit_d,
            status=PassRequest.Status.SUBMITTED,
        )
        url = reverse("requests:moderation")
        client.post(
            url,
            {"action": "approve_pass", "target_id": pr.pk, "tab": "passes"},
            follow=True,
        )
        pr.refresh_from_db()
        assert pr.status == PassRequest.Status.APPROVED

        client.post(
            url,
            {
                "action": "reject_pass",
                "target_id": pr.pk,
                "comment": "Отказ СБ",
                "tab": "passes",
            },
            follow=True,
        )
        pr.refresh_from_db()
        assert pr.status == PassRequest.Status.REJECTED
        assert pr.moderator_comment == "Отказ СБ"

    def test_publish_and_reject_squad_revision(self, client, admin_user, user):
        client.force_login(admin_user)
        direction = Direction.objects.create(name="Педагогическое", slug="ped")
        squad = Squad.objects.create(
            name="СПО Луч",
            slug="spo-luch",
            direction=direction,
            motto="Старый девиз",
        )
        revision = SquadPageRevision.objects.create(
            squad=squad,
            author=user,
            motto="Новый крутой девиз",
            description="Новое описание",
            status=SquadPageRevision.Status.PENDING,
        )

        url = reverse("requests:moderation")
        # Опубликовать ревизию
        client.post(
            url,
            {"action": "publish_revision", "target_id": revision.pk, "tab": "revisions"},
            follow=True,
        )
        revision.refresh_from_db()
        squad.refresh_from_db()
        assert revision.status == SquadPageRevision.Status.PUBLISHED
        assert squad.motto == "Новый крутой девиз"
        assert squad.description == "Новое описание"

        # Отклонить другую ревизию
        rev2 = SquadPageRevision.objects.create(
            squad=squad,
            author=user,
            motto="Плохой девиз",
            status=SquadPageRevision.Status.PENDING,
        )
        client.post(
            url,
            {
                "action": "reject_revision",
                "target_id": rev2.pk,
                "comment": "Не соответствует стилю",
                "tab": "revisions",
            },
            follow=True,
        )
        rev2.refresh_from_db()
        assert rev2.status == SquadPageRevision.Status.RETURNED
        assert rev2.moderator_comment == "Не соответствует стилю"
