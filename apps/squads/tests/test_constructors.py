from datetime import date

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.squads.models import Direction, Membership, Position, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture()
def direction():
    return Direction.objects.create(name="Сельскохозяйственное", icon="🌾")


@pytest.fixture()
def squad(direction):
    return Squad.objects.create(name="ССО Нива", direction=direction)


@pytest.fixture()
def commander_position():
    return Position.objects.create(name="Командир", is_staff=True, order=1)


@pytest.fixture()
def fighter_position():
    return Position.objects.create(name="Боец", is_staff=False, order=10)


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("admin@shso.ru", "pass123")


@pytest.fixture()
def squad_staff_user(squad, commander_position):
    user = User.objects.create_user("commander@shso.ru", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(user=user, squad=squad, position=commander_position, is_active=True)
    return user


@pytest.fixture()
def regular_user():
    return User.objects.create_user("student@shso.ru", "pass123", role=Role.MEMBER)


class TestSquadConstructors:
    def test_squad_create_denied_for_regular_user(self, client, regular_user):
        client.force_login(regular_user)
        url = reverse("squads:create")
        response = client.get(url)
        assert response.status_code == 403

    def test_squad_create_denied_for_squad_staff(self, client, squad_staff_user):
        client.force_login(squad_staff_user)
        url = reverse("squads:create")
        response = client.get(url)
        assert response.status_code == 403

    def test_squad_create_success_by_hq_staff(self, client, admin_user, direction):
        client.force_login(admin_user)
        url = reverse("squads:create")
        data = {
            "name": "ССО Тигр",
            "direction": direction.id,
            "founding_year": 2026,
            "motto": "Вперёд к победам!",
            "description": "Новый студенческий строительный отряд ДВФУ.",
            "is_recruiting": True,
        }
        res = client.post(url, data)
        assert res.status_code == 302
        squad_created = Squad.objects.get(name="ССО Тигр")
        assert squad_created.direction == direction
        assert squad_created.slug == "ссо-тигр"

    def test_squad_member_add_success(
        self, client, squad_staff_user, squad, regular_user, fighter_position
    ):
        client.force_login(squad_staff_user)
        url = reverse("squads:member_add", kwargs={"slug": squad.slug})
        res = client.get(url)
        assert res.status_code == 200

        data = {
            "user": regular_user.id,
            "position": fighter_position.id,
            "start_date": "2026-10-26",
        }
        res_post = client.post(url, data)
        assert res_post.status_code == 302
        membership = Membership.objects.get(user=regular_user, squad=squad)
        assert membership.position == fighter_position
        assert membership.is_active is True
        assert membership.start_date == date(2026, 10, 26)

    def test_squad_member_add_denied_for_unauthorized_user(
        self, client, regular_user, squad, fighter_position
    ):
        User.objects.create_user("candidate@shso.ru", "pass123")
        client.force_login(regular_user)
        url = reverse("squads:member_add", kwargs={"slug": squad.slug})
        res = client.get(url)
        assert res.status_code == 403
