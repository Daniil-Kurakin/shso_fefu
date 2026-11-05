from datetime import date, time

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.events.models import Event

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return User.objects.create_user("admin_event@example.com", "pass123", role=Role.ADMIN)


def test_event_creation_and_str(admin_user):
    event = Event.objects.create(
        title="Спартакиада ШСО ДВФУ",
        category=Event.Category.SPORT,
        organizer="ШСО ДВФУ",
        event_date=date(2026, 11, 20),
        start_time=time(10, 0),
        end_time=time(18, 0),
        location="Корпус S",
        description="Ежегодная спартакиада между отрядами.",
        created_by=admin_user,
    )
    assert str(event) == "Спартакиада ШСО ДВФУ (2026-11-20)"
    assert event.get_absolute_url() == reverse("events:detail", kwargs={"pk": event.pk})


def test_event_time_validation():
    event = Event(
        title="Некорректное время",
        event_date=date(2026, 11, 20),
        start_time=time(18, 0),
        end_time=time(10, 0),  # Время окончания раньше времени начала
        location="Кампус",
    )
    with pytest.raises(ValidationError):
        event.clean()
