from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.squads.models import Direction, Membership, Position, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture
def direction():
    return Direction.objects.create(name="Педагогическое", slug="pedagogicheskoe")


@pytest.fixture
def squad_a(direction):
    return Squad.objects.create(name="СПО «Лав»", slug="lav", direction=direction)


@pytest.fixture
def squad_b(direction):
    return Squad.objects.create(name="СПО «Территория Инициативы»", slug="ti", direction=direction)


@pytest.fixture
def pos_commander():
    return Position.objects.create(name="Командир", is_staff=True, can_initiate_transfer=True)


@pytest.fixture
def pos_fighter():
    return Position.objects.create(name="Боец", is_staff=False)


@pytest.fixture
def commander_a(squad_a, pos_commander):
    user = User.objects.create_user("commander_a@example.com", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(
        user=user,
        squad=squad_a,
        position=pos_commander,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    return user


@pytest.fixture
def commander_b(squad_b, pos_commander):
    user = User.objects.create_user("commander_b@example.com", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(
        user=user,
        squad=squad_b,
        position=pos_commander,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    return user


@pytest.fixture
def fighter_a(squad_a, pos_fighter):
    user = User.objects.create_user("fighter_a@example.com", "pass123", role=Role.MEMBER)
    Membership.objects.create(
        user=user,
        squad=squad_a,
        position=pos_fighter,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    return user


class TestVeteranModelMethods:
    def test_convert_to_veteran(self, squad_a, fighter_a):
        membership = squad_a.memberships.get(user=fighter_a)
        assert membership.is_active is True
        assert membership.is_veteran is False
        assert squad_a.active_members_count == 1
        assert fighter_a.is_veteran is False

        membership.convert_to_veteran()
        membership.refresh_from_db()
        fighter_a.refresh_from_db()

        assert membership.is_active is False
        assert membership.is_veteran is True
        assert membership.end_date == timezone.now().date()
        assert squad_a.active_members_count == 0
        assert fighter_a.is_veteran is True

    def test_convert_commander_revokes_staff_role(self, squad_a, commander_a):
        membership = squad_a.memberships.get(user=commander_a)
        assert commander_a.role == Role.SQUAD_STAFF

        membership.convert_to_veteran()
        commander_a.refresh_from_db()

        assert commander_a.role == Role.MEMBER

    def test_restore_to_active(self, squad_a, fighter_a):
        membership = squad_a.memberships.get(user=fighter_a)
        membership.convert_to_veteran()
        assert membership.is_veteran is True

        membership.restore_to_active()
        membership.refresh_from_db()

        assert membership.is_active is True
        assert membership.is_veteran is False
        assert membership.end_date is None
        assert squad_a.active_members_count == 1


class TestVeteranViews:
    def test_commander_can_convert_fighter_to_veteran(
        self, client, squad_a, commander_a, fighter_a
    ):
        client.force_login(commander_a)
        membership = squad_a.memberships.get(user=fighter_a)

        url = reverse(
            "squads:member_to_veteran",
            kwargs={"slug": squad_a.slug, "membership_id": membership.pk},
        )
        resp = client.post(url, {"action": "to_veteran"})

        assert resp.status_code == 302
        assert resp.url == squad_a.get_absolute_url()

        membership.refresh_from_db()
        assert membership.is_veteran is True
        assert membership.is_active is False

    def test_commander_of_other_squad_forbidden(self, client, squad_a, commander_b, fighter_a):
        # Комсостав отряда Б не может переводить бойцов отряда А в ветераны
        client.force_login(commander_b)
        membership = squad_a.memberships.get(user=fighter_a)

        url = reverse(
            "squads:member_to_veteran",
            kwargs={"slug": squad_a.slug, "membership_id": membership.pk},
        )
        resp = client.post(url, {"action": "to_veteran"})

        assert resp.status_code == 403
        membership.refresh_from_db()
        assert membership.is_active is True
        assert membership.is_veteran is False

    def test_fighter_cannot_convert_others(self, client, squad_a, fighter_a):
        client.force_login(fighter_a)
        membership = squad_a.memberships.get(user=fighter_a)

        url = reverse(
            "squads:member_to_veteran",
            kwargs={"slug": squad_a.slug, "membership_id": membership.pk},
        )
        resp = client.post(url, {"action": "to_veteran"})

        assert resp.status_code == 403

    def test_squad_detail_displays_veterans_and_actions(
        self, client, squad_a, commander_a, fighter_a
    ):
        membership = squad_a.memberships.get(user=fighter_a)
        membership.convert_to_veteran()

        # Страница для командира: видна секция «Ветераны отряда»
        client.force_login(commander_a)
        resp = client.get(squad_a.get_absolute_url())
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")

        assert "Ветераны отряда" in content
        assert fighter_a.get_full_name() in content
        assert "Вернуть" in content

    def test_user_profile_shows_veteran_badge(self, client, squad_a, fighter_a):
        membership = squad_a.memberships.get(user=fighter_a)
        membership.convert_to_veteran()

        client.force_login(fighter_a)
        resp = client.get(reverse("accounts:profile"))
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")

        assert "Ветеран" in content
