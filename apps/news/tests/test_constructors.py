import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.news.models import News
from apps.squads.models import Direction, Membership, Position, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture()
def direction():
    return Direction.objects.create(name="Педагогическое", icon="🧸")


@pytest.fixture()
def squad(direction):
    return Squad.objects.create(name="СПО Искра", direction=direction)


@pytest.fixture()
def staff_position():
    return Position.objects.create(name="Командир", is_staff=True, order=1)


@pytest.fixture()
def fighter_position():
    return Position.objects.create(name="Боец", is_staff=False, order=10)


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("admin@shso.ru", "pass123")


@pytest.fixture()
def squad_staff_user(squad, staff_position):
    user = User.objects.create_user("staff@shso.ru", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(user=user, squad=squad, position=staff_position, is_active=True)
    return user


@pytest.fixture()
def regular_member_user():
    return User.objects.create_user("member@shso.ru", "pass123", role=Role.MEMBER)


class TestNewsConstructor:
    def test_anonymous_redirected_to_login(self, client):
        url = reverse("news:create")
        response = client.get(url)
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_regular_member_denied(self, client, regular_member_user):
        client.force_login(regular_member_user)
        url = reverse("news:create")
        response = client.get(url)
        assert response.status_code == 403

    def test_hq_staff_can_open_create_page(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("news:create")
        response = client.get(url)
        assert response.status_code == 200
        assert "form" in response.context

    def test_hq_staff_can_create_published_news(self, client, admin_user, squad):
        client.force_login(admin_user)
        url = reverse("news:create")
        data = {
            "title": "Новость от штаба",
            "category": News.Category.ANNOUNCEMENTS,
            "organizer": News.Organizer.SHSO,
            "squad": squad.id,
            "lead": "Краткий анонс для ленты",
            "content": "Полный текст важной новости штаба.",
            "status": News.Status.PUBLISHED,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        created = News.objects.get(title="Новость от штаба")
        assert created.author == admin_user
        assert created.status == News.Status.PUBLISHED
        assert created.squad == squad

    def test_squad_staff_can_create_draft_for_own_squad(self, client, squad_staff_user, squad):
        client.force_login(squad_staff_user)
        url = reverse("news:create")
        data = {
            "title": "Отрядная новость Искры",
            "category": News.Category.EVENTS,
            "organizer": News.Organizer.SHSO,
            "squad": squad.id,
            "lead": "Анонс отряда",
            "content": "Отряд провёл мероприятие.",
            "status": News.Status.PENDING,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        created = News.objects.get(title="Отрядная новость Искры")
        assert created.author == squad_staff_user
        assert created.status == News.Status.PENDING

    def test_squad_staff_can_edit_own_squad_news(
        self, client, squad_staff_user, squad, regular_member_user
    ):
        news = News.objects.create(
            title="Старая новость Искры",
            content="Старый текст",
            author=squad_staff_user,
            squad=squad,
            status=News.Status.DRAFT,
        )
        client.force_login(squad_staff_user)
        url = reverse("news:edit", kwargs={"slug": news.slug})
        response = client.get(url)
        assert response.status_code == 200

        data = {
            "title": "Обновленная новость Искры",
            "category": News.Category.EVENTS,
            "organizer": News.Organizer.SHSO,
            "squad": squad.id,
            "lead": "Обновленный анонс",
            "content": "Обновленный текст.",
            "status": News.Status.PENDING,
        }
        res_post = client.post(url, data)
        assert res_post.status_code == 302
        news.refresh_from_db()
        assert news.title == "Обновленная новость Искры"

    def test_unauthorized_user_cannot_edit_news(
        self, client, admin_user, regular_member_user, squad
    ):
        news = News.objects.create(
            title="Чужая новость",
            content="Чужой текст",
            author=admin_user,
            squad=squad,
            status=News.Status.PUBLISHED,
        )
        client.force_login(regular_member_user)
        url = reverse("news:edit", kwargs={"slug": news.slug})
        response = client.get(url)
        assert response.status_code == 403
