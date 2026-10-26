from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.news.models import News
from apps.squads.models import Direction, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture()
def author():
    return User.objects.create_user("author@example.com", "pass-12345")


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("boss@example.com", "pass-12345")


@pytest.fixture()
def squad():
    direction = Direction.objects.create(name="Проводники", icon="🚆")
    return Squad.objects.create(name="ССО Стрела", direction=direction)


@pytest.fixture()
def published_news(author, squad):
    return News.objects.create(
        title="Победа отряда Стрела",
        lead="Анонс победы",
        content="Подробный текст о победе",
        author=author,
        squad=squad,
        category=News.Category.ACHIEVEMENTS,
        organizer=News.Organizer.SHSO,
        status=News.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=2),
    )


@pytest.fixture()
def draft_news(author):
    return News.objects.create(
        title="Секретный черновик",
        content="Текст черновика",
        author=author,
        status=News.Status.DRAFT,
    )


class TestNewsListView:
    def test_news_list_renders_200(self, client, published_news):
        url = reverse("news:list")
        response = client.get(url)
        assert response.status_code == 200
        assert published_news.title.encode() in response.content

    def test_news_list_filter_category(self, client, published_news):
        url = reverse("news:list")
        # Фильтр подходящей категории
        response = client.get(url, {"category": News.Category.ACHIEVEMENTS})
        assert response.status_code == 200
        assert published_news.title.encode() in response.content

        # Фильтр неподходящей категории
        response = client.get(url, {"category": News.Category.ANNOUNCEMENTS})
        assert response.status_code == 200
        assert published_news.title.encode() not in response.content

    def test_news_list_search(self, client, published_news):
        url = reverse("news:list")
        response = client.get(url, {"q": "Стрела"})
        assert response.status_code == 200
        assert published_news.title.encode() in response.content

        response = client.get(url, {"q": "НесуществующееСлово123"})
        assert response.status_code == 200
        assert published_news.title.encode() not in response.content

    def test_draft_news_not_in_public_list(self, client, draft_news):
        url = reverse("news:list")
        response = client.get(url)
        assert draft_news.title.encode() not in response.content


class TestNewsDetailView:
    def test_published_news_detail_accessible(self, client, published_news):
        url = reverse("news:detail", kwargs={"slug": published_news.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert published_news.title.encode() in response.content
        assert published_news.content.encode() in response.content

    def test_draft_news_404_for_guest(self, client, draft_news):
        url = reverse("news:detail", kwargs={"slug": draft_news.slug})
        response = client.get(url)
        assert response.status_code == 404

    def test_draft_news_accessible_for_author(self, client, draft_news, author):
        client.force_login(author)
        url = reverse("news:detail", kwargs={"slug": draft_news.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert draft_news.title.encode() in response.content

    def test_draft_news_accessible_for_admin(self, client, draft_news, admin_user):
        client.force_login(admin_user)
        url = reverse("news:detail", kwargs={"slug": draft_news.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert draft_news.title.encode() in response.content
