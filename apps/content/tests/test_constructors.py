import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.content.models import (
    CustomPage,
    FAQCategory,
    FAQItem,
    GlossaryTerm,
    KnowledgeArticle,
    KnowledgeCategory,
    PageBlock,
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

    def test_page_builder_permissions(self, client, regular_user, admin_user):
        client.force_login(regular_user)
        url = reverse("content:page_create")
        assert client.get(url).status_code == 403

        client.force_login(admin_user)
        assert client.get(url).status_code == 200

    def test_page_builder_create_and_detail(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("content:page_create")
        data = {
            "title": "История студотрядов ДВФУ",
            "slug": "history-fefu",
            "summary": "Летопись трудовых семестров Дальневосточного университета",
            "is_published": True,
            "blocks-TOTAL_FORMS": "1",
            "blocks-INITIAL_FORMS": "0",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-block_type": "hero",
            "blocks-0-title": "Более полувека традиций",
            "blocks-0-subtitle": "От первых студенческих строек до космодрома Восточный",
            "blocks-0-content": "Подробный исторический очерк...",
            "blocks-0-button_text": "Узнать больше",
            "blocks-0-button_url": "/squads/",
            "blocks-0-order": "0",
            "blocks-0-is_active": "on",
        }
        res = client.post(url, data)
        assert res.status_code == 302
        page = CustomPage.objects.get(slug="history-fefu")
        assert page.title == "История студотрядов ДВФУ"
        assert page.blocks.count() == 1
        block = page.blocks.first()
        assert block.block_type == "hero"
        assert block.button_text == "Узнать больше"

        # Публичный просмотр
        client.logout()
        detail_url = reverse("content:page_detail", kwargs={"slug": "history-fefu"})
        detail_res = client.get(detail_url)
        assert detail_res.status_code == 200
        assert "Более полувека традиций" in detail_res.content.decode("utf-8")

    def test_page_builder_update_and_draft_status(self, client, admin_user):
        page = CustomPage.objects.create(
            title="Черновик страницы",
            slug="draft-page",
            is_published=False,
            author=admin_user,
        )
        PageBlock.objects.create(
            page=page,
            block_type="text",
            title="Секция 1",
            content="Содержимое черновика",
            order=0,
        )

        # Неопубликованная страница скрыта от гостей
        detail_url = reverse("content:page_detail", kwargs={"slug": "draft-page"})
        assert client.get(detail_url).status_code == 404

        # Доступна администратору
        client.force_login(admin_user)
        assert client.get(detail_url).status_code == 200

        # Редактирование через конструктор
        edit_url = reverse("content:page_edit", kwargs={"slug": "draft-page"})
        edit_page = client.get(edit_url)
        assert edit_page.status_code == 200

        block = page.blocks.first()
        update_data = {
            "title": "Опубликованная страница",
            "slug": "draft-page",
            "summary": "Теперь доступна всем",
            "is_published": True,
            "blocks-TOTAL_FORMS": "1",
            "blocks-INITIAL_FORMS": "1",
            "blocks-MIN_NUM_FORMS": "0",
            "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-id": block.id,
            "blocks-0-block_type": "cards",
            "blocks-0-title": "Преимущества",
            "blocks-0-content": "Опыт | Первая работа | /jobs\nДружба | Верные товарищи",
            "blocks-0-order": "0",
            "blocks-0-is_active": "on",
        }
        res = client.post(edit_url, update_data)
        assert res.status_code == 302
        page.refresh_from_db()
        assert page.title == "Опубликованная страница"
        assert page.is_published is True
        block.refresh_from_db()
        assert block.block_type == "cards"
        cards = block.parsed_cards()
        assert len(cards) == 2
        assert cards[0]["title"] == "Опыт"
        assert cards[0]["url"] == "/jobs"

    def test_page_delete(self, client, admin_user):
        page = CustomPage.objects.create(
            title="Удаляемая страница",
            slug="to-delete",
        )
        client.force_login(admin_user)
        del_url = reverse("content:page_delete", kwargs={"slug": page.slug})
        res = client.post(del_url)
        assert res.status_code == 302
        assert not CustomPage.objects.filter(slug="to-delete").exists()

    def test_moderation_pages_tab(self, client, admin_user):
        CustomPage.objects.create(title="Страница для админки", slug="admin-page")
        client.force_login(admin_user)
        url = reverse("requests:moderation") + "?tab=pages"
        res = client.get(url)
        assert res.status_code == 200
        assert "Страница для админки" in res.content.decode("utf-8")
