import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.squads.models import Direction, Membership, Position, Squad
from apps.vacancies.models import Vacancy

pytestmark = pytest.mark.django_db


@pytest.fixture()
def direction():
    return Direction.objects.create(name="Сервисное", icon="☕")


@pytest.fixture()
def squad(direction):
    return Squad.objects.create(name="ССО Приморье", direction=direction)


@pytest.fixture()
def staff_position():
    return Position.objects.create(name="Мастер", is_staff=True, order=2)


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("admin@shso.ru", "pass123")


@pytest.fixture()
def squad_staff_user(squad, staff_position):
    user = User.objects.create_user("master@shso.ru", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(user=user, squad=squad, position=staff_position, is_active=True)
    return user


@pytest.fixture()
def regular_member_user():
    return User.objects.create_user("student@shso.ru", "pass123", role=Role.MEMBER)


class TestVacancyConstructor:
    def test_anonymous_redirected_to_login(self, client):
        url = reverse("vacancies:create")
        response = client.get(url)
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_regular_member_denied(self, client, regular_member_user):
        client.force_login(regular_member_user)
        url = reverse("vacancies:create")
        response = client.get(url)
        assert response.status_code == 403

    def test_squad_staff_can_create_squad_vacancy(self, client, squad_staff_user, squad):
        client.force_login(squad_staff_user)
        url = reverse("vacancies:create")
        response = client.get(url)
        assert response.status_code == 200

        data = {
            "title": "Набор в ССО Приморье 2026",
            "type": Vacancy.Type.JOIN_SQUAD,
            "squad": squad.id,
            "description": "Ищем активных ребят для работы на всероссийской стройке.",
            "requirements": "Студент ДВФУ, 18+",
            "status": Vacancy.Status.OPEN,
        }
        res_post = client.post(url, data)
        assert res_post.status_code == 302
        vacancy = Vacancy.objects.get(title="Набор в ССО Приморье 2026")
        assert vacancy.squad == squad
        assert vacancy.type == Vacancy.Type.JOIN_SQUAD

    def test_hq_staff_can_create_campus_job(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("vacancies:create")
        data = {
            "title": "Администратор коворкинга Аякс",
            "type": Vacancy.Type.CAMPUS_JOB,
            "description": "Работа на территории кампуса ДВФУ в корпусе А.",
            "requirements": "Ответственность, грамотная речь.",
            "salary": "35 000 руб.",
            "status": Vacancy.Status.OPEN,
        }
        res_post = client.post(url, data)
        assert res_post.status_code == 302
        vacancy = Vacancy.objects.get(title="Администратор коворкинга Аякс")
        assert vacancy.squad is None
        assert vacancy.type == Vacancy.Type.CAMPUS_JOB

    def test_squad_staff_can_edit_own_vacancy(self, client, squad_staff_user, squad):
        vacancy = Vacancy.objects.create(
            title="Старая вакансия",
            type=Vacancy.Type.JOIN_SQUAD,
            squad=squad,
            description="Старое описание",
            status=Vacancy.Status.OPEN,
        )
        client.force_login(squad_staff_user)
        url = reverse("vacancies:edit", kwargs={"slug": vacancy.slug})
        res = client.get(url)
        assert res.status_code == 200

        res_post = client.post(
            url,
            {
                "title": "Обновленная вакансия",
                "type": Vacancy.Type.JOIN_SQUAD,
                "squad": squad.id,
                "description": "Новое описание условий целины",
                "status": Vacancy.Status.CLOSED,
            },
        )
        assert res_post.status_code == 302
        vacancy.refresh_from_db()
        assert vacancy.title == "Обновленная вакансия"
        assert vacancy.status == Vacancy.Status.CLOSED
