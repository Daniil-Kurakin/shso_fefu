from datetime import time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.requests.models import (
    BookedPremise,
    CampusPremise,
    PassRequest,
    PassVisitor,
    RoomBookingRequest,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def applicant():
    return User.objects.create_user(
        "applicant@example.com", "pass-12345", full_name="Иван Заявитель"
    )


@pytest.fixture
def moderator():
    return User.objects.create_superuser(
        "moderator@example.com", "pass-12345", full_name="Штаб Модератор"
    )


@pytest.fixture
def room():
    return CampusPremise.objects.create(
        name="Аудитория А826 (Штаб)",
        building=CampusPremise.Building.CORPUS_A,
        room_number="А826",
        capacity=30,
    )


class TestCampusPremiseModel:
    def test_str(self, room):
        assert "Аудитория А826 (Штаб)" in str(room)
        assert "Корпус A" in str(room)


class TestRoomBookingRequestModel:
    def test_create_and_str(self, applicant, room):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Собрание отряда",
            event_date=tomorrow,
            start_time=time(18, 0),
            end_time=time(20, 0),
        )
        assert "Собрание отряда" in str(booking)
        assert booking.status == RoomBookingRequest.Status.SUBMITTED

    def test_invalid_time_interval(self, applicant, room):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = RoomBookingRequest(
            user=applicant,
            room=room,
            event_name="Ошибка времени",
            event_date=tomorrow,
            start_time=time(20, 0),
            end_time=time(18, 0),
        )
        with pytest.raises(ValidationError) as exc:
            booking.clean()
        assert "end_time" in exc.value.error_dict

    def test_collision_detection_and_approval(self, applicant, moderator, room):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking1 = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Первая бронь",
            event_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        booking2 = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Вторая бронь (пересекается)",
            event_date=tomorrow,
            start_time=time(15, 0),
            end_time=time(17, 0),
        )

        # До одобрения есть конфликт среди поданных заявок
        conflicts = booking1.get_conflicting_bookings()
        assert booking2 in conflicts
        assert booking1.has_approved_collision() is False

        # Одобряем первую заявку
        booking1.approve(moderator=moderator, comment="Одобрено, ключ в А826")
        assert booking1.status == RoomBookingRequest.Status.APPROVED
        assert booking1.reviewed_by == moderator

        # Вторая заявка теперь видит одобренную коллизию
        assert booking2.has_approved_collision() is True

        # Попытка одобрить вторую заявку вызывает ValidationError
        with pytest.raises(ValidationError):
            booking2.approve(moderator=moderator)

    def test_reject_and_cancel(self, applicant, moderator, room):
        tomorrow = timezone.localdate() + timedelta(days=2)
        booking = RoomBookingRequest.objects.create(
            user=applicant,
            room=room,
            event_name="Бронь на отмену",
            event_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        booking.reject(moderator=moderator, comment="Аудитория закрыта на ремонт")
        assert booking.status == RoomBookingRequest.Status.REJECTED
        assert booking.moderator_comment == "Аудитория закрыта на ремонт"

        booking.cancel()
        assert booking.status == RoomBookingRequest.Status.CANCELLED

    def test_booked_premise_creation_and_validation(self, applicant):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = RoomBookingRequest.objects.create(
            user=applicant,
            event_name="Мультирум событие",
            event_date=tomorrow,
        )
        premise = BookedPremise.objects.create(
            booking=booking,
            custom_room="А826 Коворкинг",
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        assert "А826 Коворкинг" in str(premise)
        assert premise.room_name == "А826 Коворкинг"
        assert "А826 Коворкинг" in booking.rooms_display

        # Невалидное время: окончание раньше начала
        invalid_premise = BookedPremise(
            booking=booking,
            custom_room="D504",
            start_time=time(15, 0),
            end_time=time(14, 0),
        )
        with pytest.raises(ValidationError):
            invalid_premise.clean()

        # Пустая аудитория
        empty_premise = BookedPremise(
            booking=booking,
            start_time=time(14, 0),
            end_time=time(15, 0),
        )
        with pytest.raises(ValidationError):
            empty_premise.clean()


class TestPassRequestModel:
    def test_create_and_auto_scheduled_purge(self, applicant):
        visit_d = timezone.localdate() + timedelta(days=3)
        pass_req = PassRequest.objects.create(
            user=applicant,
            title="Гостевой лектор",
            pass_type=PassRequest.PassType.INDIVIDUAL,
            visit_date=visit_d,
            entry_point="Северные ворота",
        )
        assert pass_req.data_deletion_scheduled_at == visit_d + timedelta(days=30)
        assert pass_req.is_data_purged is False

    def test_vehicle_pass_requires_car_number(self, applicant):
        visit_d = timezone.localdate() + timedelta(days=3)
        pass_req = PassRequest(
            user=applicant,
            title="Доставка декораций",
            pass_type=PassRequest.PassType.VEHICLE,
            visit_date=visit_d,
            car_model="ГАЗель",
            car_number="",
        )
        with pytest.raises(ValidationError) as exc:
            pass_req.clean()
        assert "car_number" in exc.value.error_dict

    def test_purge_personal_data_152fz(self, applicant):
        visit_d = timezone.localdate() + timedelta(days=1)
        pass_req = PassRequest.objects.create(
            user=applicant,
            title="Семинар",
            pass_type=PassRequest.PassType.GROUP,
            visit_date=visit_d,
        )
        visitor = PassVisitor.objects.create(
            request=pass_req,
            full_name="Сергеев Сергей",
            document_type=PassVisitor.DocumentType.PASSPORT,
            document_data="0515 999888",
            phone="+79991234567",
        )

        pass_req.purge_personal_data()
        visitor.refresh_from_db()
        pass_req.refresh_from_db()

        assert pass_req.is_data_purged is True
        assert "152-ФЗ" in visitor.document_data
        assert visitor.phone == ""
