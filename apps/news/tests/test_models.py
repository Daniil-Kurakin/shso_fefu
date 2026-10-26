from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.news.models import News, NewsImage
from apps.squads.models import Direction, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture()
def author():
    return User.objects.create_user("author@example.com", "pass-12345")


@pytest.fixture()
def squad():
    direction = Direction.objects.create(name="Сервисное", icon="⚡")
    return Squad.objects.create(name="Сервис ДВФУ", direction=direction)


def test_news_creation_and_slug(author):
    news = News.objects.create(
        title="Старт трудового семестра 2026",
        content="Текст новости о семестре",
        author=author,
        status=News.Status.DRAFT,
    )
    assert news.slug == "старт-трудового-семестра-2026"
    assert news.status == News.Status.DRAFT
    assert str(news) == "Старт трудового семестра 2026"


def test_news_published_manager(author):
    now = timezone.now()
    # Опубликованная
    published = News.objects.create(
        title="Опубликованная",
        content="Контент",
        author=author,
        status=News.Status.PUBLISHED,
        published_at=now - timedelta(days=1),
    )
    # Черновик
    News.objects.create(
        title="Черновик",
        content="Контент",
        author=author,
        status=News.Status.DRAFT,
    )
    # Запланированная в будущем
    News.objects.create(
        title="Будущая",
        content="Контент",
        author=author,
        status=News.Status.PUBLISHED,
        published_at=now + timedelta(days=1),
    )

    published_qs = News.objects.published()
    assert published in published_qs
    assert published_qs.count() == 1


def test_news_gallery_image(author):
    news = News.objects.create(
        title="Событие с галереей",
        content="Контент",
        author=author,
    )
    image = NewsImage.objects.create(
        news=news,
        image="test.jpg",
        caption="Фото 1",
        order=1,
    )
    assert image.news == news
    assert "Событие с галереей" in str(image)
