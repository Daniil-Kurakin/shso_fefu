from datetime import time, timedelta

import pytest
from django.contrib.admin.sites import site
from django.utils import timezone

from apps.accounts.models import User
from apps.requests.admin import PassRequestAdmin, RoomBookingRequestAdmin
from apps.requests.models import CampusPremise, PassRequest, PassVisitor, RoomBookingRequest

pytestmark = pytest.mark.django_db


class DummyMessageStorage:
    def __init__(self, request=None):
        self.messages = []

    def add(self, level, message, extra_tags=""):
        self.messages.append(message)

    def __iter__(self):
        return iter(self.messages)


@pytest.fixture
def moderator():
    return User.objects.create_superuser("admin_req@example.com", "pass-admin")


@pytest.fixture
def applicant():
    return User.objects.create_user("app_req@example.com", "pass-app")


@pytest.fixture
def room():
    return CampusPremise.objects.create(name="Аудитория А826", building="A")


class TestRequestsAdmin:
    def test_room_booking_admin_actions(self, rf, moderator, applicant, room):
        tomorrow = timezone.localdate() + timedelta(days=2)
        booking1 = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Бронь 1",
            event_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        booking2 = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Бронь 2",
            event_date=tomorrow,
            start_time=time(17, 0),
            end_time=time(18, 0),
        )

        admin_obj = RoomBookingRequestAdmin(RoomBookingRequest, site)
        request = rf.get("/admin/requests/roombookingrequest/")
        request.user = moderator
        request._messages = DummyMessageStorage(request)

        # Одобрение через действие админки
        admin_obj.action_approve(request, RoomBookingRequest.objects.filter(pk=booking1.pk))
        booking1.refresh_from_db()
        assert booking1.status == RoomBookingRequest.Status.APPROVED
        assert booking1.reviewed_by == moderator

        # Проверка отображения статуса коллизий
        status_html = admin_obj.collision_status(booking1)
        assert "✓ Одобрена" in status_html

        # Отклонение через действие админки
        admin_obj.action_reject(request, RoomBookingRequest.objects.filter(pk=booking2.pk))
        booking2.refresh_from_db()
        assert booking2.status == RoomBookingRequest.Status.REJECTED

    def test_pass_request_admin_export_csv_and_purge(self, rf, moderator, applicant):
        visit_d = timezone.localdate() + timedelta(days=3)
        pr = PassRequest.objects.create(
            user=applicant,
            title="Спикер форума",
            visit_date=visit_d,
            entry_point="Северные ворота",
            car_number="А001АА 125",
        )
        PassVisitor.objects.create(
            request=pr,
            full_name="Ковалев Константин",
            document_type=PassVisitor.DocumentType.PASSPORT,
            document_data="0515 333444",
            organization="ДВО РАН",
        )

        admin_obj = PassRequestAdmin(PassRequest, site)
        request = rf.get("/admin/requests/passrequest/")
        request.user = moderator
        request._messages = DummyMessageStorage(request)

        # Выгрузка в CSV для бюро пропусков
        qs = PassRequest.objects.filter(pk=pr.pk)
        response = admin_obj.export_pass_list_csv(request, qs)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv; charset=utf-8-sig"
        content = response.content.decode("utf-8-sig")
        assert "Ковалев Константин" in content
        assert "0515 333444" in content
        assert "А001АА 125" in content

        # Одобрение пропуска
        admin_obj.action_approve(request, qs)
        pr.refresh_from_db()
        assert pr.status == PassRequest.Status.APPROVED

        # Очистка ПДн через админку
        admin_obj.action_purge_data(request, qs)
        pr.refresh_from_db()
        assert pr.is_data_purged is True
