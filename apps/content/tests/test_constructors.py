import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.content.models import (
    FAQCategory,
    FAQItem,
    GlossaryTerm,
    KnowledgeArticle,
    KnowledgeCategory,
)
from apps.squads.models import Direction, Membership, Position, Squad

pytestmark = pytest.mark.django_db


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("admin@shso.ru", "pass123")


@pytest.fixture()
def regular_user():
    return User.objects.create_user("student@shso.ru", "pass123", role=Role.MEMBER)


@pytest.fixture()
def squad_staff_user():
    direction = Direction.objects.create(name="Медицинское", icon="🩺")
    squad = Squad.objects.create(name="СМО Феникс", direction=direction)
    pos = Position.objects.create(name="Комиссар", is_staff=True, order=2)
    user = User.objects.create_user("kom@shso.ru", "pass123", role=Role.SQUAD_STAFF)
    Membership.objects.create(user=user, squad=squad, position=pos, is_active=True)
    return user


@pytest.fixture()
def knowledge_category():
    return KnowledgeCategory.objects.create(title="Традиции", slug="traditions", icon="⭐")


@pytest.fixture()
def faq_category():
    return FAQCategory.objects.create(title="Общие вопросы", slug="general")


class TestContentConstructors:
    def test_knowledge_create_forbidden_for_regular_user(self, client, regular_user):
        client.force_login(regular_user)
        url = reverse("content:knowledge_create")
        response = client.get(url)
        assert response.status_code == 403

    def test_knowledge_create_success_by_hq_staff(self, client, admin_user, knowledge_category):
        client.force_login(admin_user)
        url = reverse("content:knowledge_create")
        data = {
            "category": knowledge_category.id,
            "title": "История отрядной песни",
            "summary": "Как зарождались спевки студотрядов",
            "content": "Подробный исторический экскурс...",
            "is_published": True,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        article = KnowledgeArticle.objects.get(title="История отрядной песни")
        assert article.category == knowledge_category
        assert article.is_published is True

    def test_knowledge_edit_success(self, client, admin_user, knowledge_category):
        article = KnowledgeArticle.objects.create(
            category=knowledge_category,
            title="Положение о нашивках",
            summary="Правила ношения",
            content="Инструкция...",
            is_published=True,
        )
        client.force_login(admin_user)
        url = reverse(
            "content:knowledge_edit",
            kwargs={"category_slug": knowledge_category.slug, "slug": article.slug},
        )
        res = client.get(url)
        assert res.status_code == 200

        res_post = client.post(
            url,
            {
                "category": knowledge_category.id,
                "title": "Положение о нашивках и шевронах",
                "summary": "Обновленные правила ношения",
                "content": "Инструкция 2026...",
                "is_published": True,
            },
        )
        assert res_post.status_code == 302
        article.refresh_from_db()
        assert article.title == "Положение о нашивках и шевронах"

    def test_faq_create_by_hq_staff(self, client, admin_user, faq_category):
        client.force_login(admin_user)
        url = reverse("content:faq_create")
        data = {
            "category": faq_category.id,
            "question": "Как получить целику?",
            "answer": "Целинка выдаётся после успешного прохождения школы подготовки.",
            "order": 1,
            "is_published": True,
        }
        res = client.post(url, data)
        assert res.status_code == 302
        item = FAQItem.objects.get(question="Как получить целику?")
        assert item.category == faq_category

    def test_glossary_create_by_squad_staff(self, client, squad_staff_user):
        client.force_login(squad_staff_user)
        url = reverse("content:glossary_create")
        data = {
            "term": "Фотокросс",
            "definition": "Творческое соревнование отрядных фотографов на заданную тему.",
            "synonyms": "фотобитва, фотоохота",
        }
        res = client.post(url, data)
        assert res.status_code == 302
        term = GlossaryTerm.objects.get(term="Фотокросс")
        assert term.letter == "Ф"

    def test_glossary_create_denied_for_regular_member(self, client, regular_user):
        client.force_login(regular_user)
        url = reverse("content:glossary_create")
        res = client.get(url)
        assert res.status_code == 403
