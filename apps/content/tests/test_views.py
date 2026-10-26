import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.content.models import Quote, StaffMember

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
