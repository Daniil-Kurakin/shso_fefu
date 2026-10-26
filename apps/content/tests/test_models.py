import datetime

import pytest
from django.core.cache import cache

from apps.content.models import Quote, SiteSetting, StaffMember

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_quote_creation():
    quote = Quote.objects.create(
        text="Труд крут!",
        author="Командир штаба",
        author_title="Ветеран РСО",
    )
    assert str(quote).startswith("«Труд крут!...")
    assert quote.is_active is True


def test_quote_of_the_day_pinned():
    today = datetime.date(2026, 11, 1)
    Quote.objects.create(
        text="Обычная цитата",
        author="Боец 1",
        is_active=True,
    )
    pinned_quote = Quote.objects.create(
        text="Закреплённая цитата на праздник",
        author="Командир",
        is_active=True,
        pinned_date=today,
    )

    result = Quote.get_quote_of_the_day(for_date=today)
    assert result == pinned_quote


def test_quote_of_the_day_rotation():
    q1 = Quote.objects.create(text="Цитата 1", author="Автор 1")
    q2 = Quote.objects.create(text="Цитата 2", author="Автор 2")

    day1 = datetime.date(2026, 11, 1)
    day2 = datetime.date(2026, 11, 2)

    res1 = Quote.get_quote_of_the_day(for_date=day1)
    res2 = Quote.get_quote_of_the_day(for_date=day2)

    assert res1 in {q1, q2}
    assert res2 in {q1, q2}
    # Разные дни дают детерминированный циклический результат
    assert res1 != res2


def test_quote_of_the_day_empty():
    assert Quote.get_quote_of_the_day() is None


def test_staff_member_creation():
    member = StaffMember.objects.create(
        full_name="Иванов Иван",
        position="Начальник штаба",
        email="chief@dvfu.ru",
        order=1,
    )
    assert str(member) == "Иванов Иван (Начальник штаба)"
    assert member.is_active is True


def test_site_setting_get_and_cache():
    # Дефолтное значение, если нет в БД
    assert SiteSetting.get("unknown_key", default="fallback") == "fallback"

    setting = SiteSetting.objects.create(
        key="squads_count",
        value="22",
        value_en="22",
        year=2026,
        source="Трудовой семестр 2026",
    )
    assert SiteSetting.get("squads_count") == "22"
    assert str(setting) == "squads_count: 22"

    # Обновление настройки сбрасывает кэш
    setting.value = "25"
    setting.save()
    assert SiteSetting.get("squads_count") == "25"


def test_site_setting_get_object():
    SiteSetting.objects.create(
        key="students_count",
        value="900+",
        year=2026,
        source="Официальные данные",
    )
    obj = SiteSetting.get_setting_object("students_count")
    assert obj is not None
    assert obj.year == 2026
    assert obj.source == "Официальные данные"
