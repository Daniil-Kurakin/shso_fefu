import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.content.models import (
    FAQCategory,
    FAQItem,
    GlossaryTerm,
    KnowledgeArticle,
    KnowledgeCategory,
    Quote,
    StaffMember,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_contacts_page_renders_200(client):
    url = reverse("content:contacts")
    response = client.get(url)
    assert response.status_code == 200
    assert "Контакты и руководство".encode() in response.content


def test_contacts_page_displays_staff(client):
    StaffMember.objects.create(
        full_name="Сергей Петров",
        position="Комиссар штаба",
        responsibility="Куратор медиа-центра",
        email="komissar@dvfu.ru",
        is_active=True,
    )
    url = reverse("content:contacts")
    response = client.get(url)
    assert response.status_code == 200
    assert "Сергей Петров".encode() in response.content
    assert "Комиссар штаба".encode() in response.content
    assert "Куратор медиа-центра".encode() in response.content


def test_home_page_displays_quote_of_the_day(client):
    Quote.objects.create(
        text="Студенческий отряд — это школа жизни!",
        author="Даниил",
        author_title="Командир",
        is_active=True,
    )
    url = reverse("core:home")
    response = client.get(url)
    assert response.status_code == 200
    assert "Студенческий отряд — это школа жизни!".encode() in response.content
    assert "Даниил".encode() in response.content


def test_site_settings_in_template_context(client):
    url = reverse("core:home")
    response = client.get(url)
    assert response.status_code == 200
    assert "site_settings" in response.context
    assert "hq_office" in response.context["site_settings"]


def test_knowledge_index_and_search(client):
    cat = KnowledgeCategory.objects.create(title="Инструкции", icon="📘")
    art1 = KnowledgeArticle.objects.create(
        category=cat,
        title="Как пройти медосмотр",
        summary="Инструкция по врачам",
        content="Текст о медкомиссии",
        pinned=True,
    )
    art2 = KnowledgeArticle.objects.create(
        category=cat,
        title="Охрана труда на стройке",
        summary="Правила каски",
        content="Инструктаж по безопасности",
    )

    url = reverse("content:knowledge_index")
    # Главная страница
    res = client.get(url)
    assert res.status_code == 200
    assert "Инструкции".encode() in res.content
    assert art1.title.encode() in res.content

    # Поиск по запросу
    res_search = client.get(f"{url}?q=медосмотр")
    assert res_search.status_code == 200
    assert art1.title.encode() in res_search.content
    assert art2.title.encode() not in res_search.content


def test_knowledge_category_and_detail(client):
    cat = KnowledgeCategory.objects.create(title="Традиции", slug="traditions")
    art = KnowledgeArticle.objects.create(
        category=cat,
        title="История отрядов ДВФУ",
        slug="history",
        summary="С чего все начиналось",
        content="Полная история движения в университете",
    )

    # Категория
    res_cat = client.get(cat.get_absolute_url())
    assert res_cat.status_code == 200
    assert "История отрядов ДВФУ".encode() in res_cat.content

    # Детальная страница
    res_detail = client.get(art.get_absolute_url())
    assert res_detail.status_code == 200
    assert "Полная история движения".encode() in res_detail.content

    # Проверка счетчика просмотров
    art.refresh_from_db()
    assert art.views_count == 1

    # Повторный запрос в той же сессии не накручивает просмотры
    client.get(art.get_absolute_url())
    art.refresh_from_db()
    assert art.views_count == 1


def test_faq_list_and_filters(client):
    cat1 = FAQCategory.objects.create(title="Лето", slug="summer")
    cat2 = FAQCategory.objects.create(title="Зима", slug="winter")
    item1 = FAQItem.objects.create(
        category=cat1,
        question="Когда выезд на целину?",
        answer="В июле.",
    )
    item2 = FAQItem.objects.create(
        category=cat2,
        question="Бывают ли зимние смены?",
        answer="Да, на новогодние праздники.",
    )

    url = reverse("content:faq")
    res = client.get(url)
    assert res.status_code == 200
    assert item1.question.encode() in res.content
    assert item2.question.encode() in res.content

    # Фильтр по категории
    res_filter = client.get(f"{url}?category=summer")
    assert item1.question.encode() in res_filter.content
    assert item2.question.encode() not in res_filter.content


def test_glossary_list_and_filters(client):
    t1 = GlossaryTerm.objects.get(term="Бойцовка")
    t2 = GlossaryTerm.objects.get(term="Целина")

    url = reverse("content:glossary")
    res = client.get(url)
    assert res.status_code == 200
    assert t1.term.encode() in res.content
    assert t2.term.encode() in res.content

    # Фильтр по букве Б
    res_b = client.get(f"{url}?letter=Б")
    assert t1.term.encode() in res_b.content
    assert t2.term.encode() not in res_b.content
