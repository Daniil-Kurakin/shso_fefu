from datetime import date, time

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.requests.models import HQRequest, HQRequestResponse
from apps.squads.models import Direction, Membership, Position, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_user():
    return User.objects.create_user("owner@example.com", "pass-12345", role=Role.OWNER)


@pytest.fixture
def admin_user():
    return User.objects.create_user("admin@example.com", "pass-12345", role=Role.ADMIN)


@pytest.fixture
def squad():
    direction = Direction.objects.create(name="Строительное", slug="stroitelnoe")
    return Squad.objects.create(
        name="ССО «Богатырь»",
        slug="bogatyr",
        direction=direction,
    )


@pytest.fixture
def fighter_user(squad):
    user = User.objects.create_user("fighter@example.com", "pass-12345", role=Role.MEMBER)
    pos = Position.objects.create(name="Боец", is_staff=False)
    Membership.objects.create(
        user=user,
        squad=squad,
        position=pos,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    return user


@pytest.fixture
def command_staff_user(squad):
    user = User.objects.create_user("commander@example.com", "pass-12345", role=Role.SQUAD_STAFF)
    pos = Position.objects.create(name="Командир", is_staff=True)
    Membership.objects.create(
        user=user,
        squad=squad,
        position=pos,
        start_date=date(2025, 1, 1),
        is_active=True,
    )
    return user


@pytest.fixture
def candidate_user():
    # Кандидат: пользователь без членства в отряде
    return User.objects.create_user("candidate@example.com", "pass-12345", role=Role.MEMBER)


@pytest.fixture
def hq_request_with_dobro(admin_user):
    return HQRequest.objects.create(
        title="Помощь на ВЭФ-2026",
        description="Требуются волонтеры для координации гостей форума.",
        customer="Фонд Росконгресс",
        level=HQRequest.Level.ALL_RUSSIAN,
        dobro_ru_url="https://dobro.ru/event/123456",
        event_date=date(2026, 9, 5),
        event_time=time(10, 0),
        location="Корпус А, уровень 4",
        status=HQRequest.Status.OPEN,
        created_by=admin_user,
    )


@pytest.fixture
def hq_request_without_dobro(admin_user):
    return HQRequest.objects.create(
        title="Уборка кампуса ДВФU",
        description="Субботник на территории кампуса.",
        customer="ШСО ДВФУ",
        level=HQRequest.Level.UNIVERSITY,
        dobro_ru_url="",
        event_date=date(2026, 5, 1),
        location="Набережная ДВФУ",
        status=HQRequest.Status.OPEN,
        created_by=admin_user,
    )


class TestHQRequestModels:
    def test_permissions_properties(
        self, owner_user, admin_user, fighter_user, command_staff_user, candidate_user
    ):
        assert owner_user.can_manage_hq_requests is True
        assert admin_user.can_manage_hq_requests is True
        assert fighter_user.can_manage_hq_requests is False
        assert candidate_user.can_manage_hq_requests is False

        assert fighter_user.is_fighter_or_staff is True
        assert command_staff_user.is_fighter_or_staff is True
        assert admin_user.is_fighter_or_staff is True
        assert owner_user.is_fighter_or_staff is True
        assert candidate_user.is_fighter_or_staff is False

    def test_hq_request_response_counting(self, hq_request_with_dobro, fighter_user):
        assert hq_request_with_dobro.responses_count == 0
        assert hq_request_with_dobro.is_user_responded(fighter_user) is False

        HQRequestResponse.objects.create(
            request=hq_request_with_dobro,
            user=fighter_user,
            comment="Готов участвовать все дни",
        )

        assert hq_request_with_dobro.responses_count == 1
        assert hq_request_with_dobro.is_user_responded(fighter_user) is True


class TestHQRequestViews:
    def test_list_view_guest(self, client, hq_request_with_dobro, hq_request_without_dobro):
        url = reverse("requests:hq_list")
        resp = client.get(url)
        assert resp.status_code == 200
        assert "Помощь на ВЭФ-2026" in resp.content.decode("utf-8")
        assert "Уборка кампуса ДВФU" in resp.content.decode("utf-8")

    def test_list_view_filters(self, client, hq_request_with_dobro, hq_request_without_dobro):
        url = reverse("requests:hq_list") + f"?level={HQRequest.Level.ALL_RUSSIAN}"
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Помощь на ВЭФ-2026" in content
        assert "Уборка кампуса ДВФU" not in content

    def test_detail_view_dobro_visibility(
        self, client, hq_request_with_dobro, hq_request_without_dobro
    ):
        # 1. Запрос со ссылкой dobro.ru — ссылка видна
        url1 = reverse("requests:hq_detail", kwargs={"pk": hq_request_with_dobro.pk})
        resp1 = client.get(url1)
        assert resp1.status_code == 200
        content1 = resp1.content.decode("utf-8")
        assert "https://dobro.ru/event/123456" in content1
        assert "ДОБРО.РФ" in content1

        # 2. Запрос без ссылки dobro.ru — плашка добро.рф НЕ отображается
        url2 = reverse("requests:hq_detail", kwargs={"pk": hq_request_without_dobro.pk})
        resp2 = client.get(url2)
        assert resp2.status_code == 200
        content2 = resp2.content.decode("utf-8")
        assert "ДОБРО.РФ" not in content2

    def test_create_view_permissions(self, client, admin_user, fighter_user):
        create_url = reverse("requests:hq_create")

        # Боец не может зайти на создание запроса (403)
        client.force_login(fighter_user)
        resp = client.get(create_url)
        assert resp.status_code == 403

        # Админ может создать запрос
        client.force_login(admin_user)
        resp = client.get(create_url)
        assert resp.status_code == 200

        data = {
            "title": "Новый фестиваль отрядов",
            "description": "Фестиваль студенческих отрядов ДВФУ.",
            "customer": "Департамент молодежной политики",
            "level": HQRequest.Level.REGIONAL,
            "dobro_ru_url": "https://dobro.ru/event/777",
            "event_date": "2026-10-15",
            "event_time": "14:00",
            "location": "Синий зал, А3",
            "status": HQRequest.Status.OPEN,
        }
        post_resp = client.post(create_url, data)
        assert post_resp.status_code == 302
        new_req = HQRequest.objects.get(title="Новый фестиваль отрядов")
        assert new_req.customer == "Департамент молодежной политики"
        assert new_req.created_by == admin_user

    def test_respond_flow_by_fighter(self, client, fighter_user, hq_request_with_dobro):
        client.force_login(fighter_user)
        respond_url = reverse("requests:hq_respond", kwargs={"pk": hq_request_with_dobro.pk})

        # Отклик
        post_resp = client.post(respond_url, {"action": "respond", "comment": "Буду с флагом!"})
        assert post_resp.status_code == 302
        assert HQRequestResponse.objects.filter(
            request=hq_request_with_dobro, user=fighter_user
        ).exists()

        # Отмена отклика
        cancel_resp = client.post(respond_url, {"action": "cancel"})
        assert cancel_resp.status_code == 302
        assert not HQRequestResponse.objects.filter(
            request=hq_request_with_dobro, user=fighter_user
        ).exists()

    def test_candidate_cannot_respond(self, client, candidate_user, hq_request_with_dobro):
        client.force_login(candidate_user)
        respond_url = reverse("requests:hq_respond", kwargs={"pk": hq_request_with_dobro.pk})

        post_resp = client.post(respond_url, {"action": "respond"})
        assert post_resp.status_code == 302
        # Отклик не должен создаться
        assert not HQRequestResponse.objects.filter(
            request=hq_request_with_dobro, user=candidate_user
        ).exists()

    def test_moderation_admin_view_hq_requests(self, client, admin_user, hq_request_with_dobro):
        client.force_login(admin_user)
        url = reverse("requests:moderation") + "?tab=hq_requests"
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Помощь на ВЭФ-2026" in content
