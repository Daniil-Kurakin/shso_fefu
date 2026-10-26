import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.squads.models import Direction, Membership, Position, Squad, SquadPageRevision

pytestmark = pytest.mark.django_db


@pytest.fixture()
def direction():
    return Direction.objects.create(name="Сервисное", icon="⚡")


@pytest.fixture()
def direction_ped():
    return Direction.objects.create(name="Педагогическое", icon="🎓")


@pytest.fixture()
def squad(direction):
    return Squad.objects.create(
        name="ССервО Спутник",
        direction=direction,
        founding_year=2020,
        is_recruiting=True,
    )


@pytest.fixture()
def target_squad(direction_ped):
    return Squad.objects.create(
        name="СПО Вместе",
        direction=direction_ped,
        founding_year=2018,
    )


@pytest.fixture()
def pos_commander():
    return Position.objects.create(
        name="Командир",
        is_staff=True,
        can_initiate_transfer=True,
    )


@pytest.fixture()
def pos_fighter():
    return Position.objects.create(
        name="Боец",
        is_staff=False,
    )


@pytest.fixture()
def commander(squad, pos_commander):
    user = User.objects.create_user("commander@example.com", "pass-12345")
    Membership.objects.create(user=user, squad=squad, position=pos_commander, is_active=True)
    return user


@pytest.fixture()
def fighter(squad, pos_fighter):
    user = User.objects.create_user("fighter@example.com", "pass-12345")
    Membership.objects.create(user=user, squad=squad, position=pos_fighter, is_active=True)
    return user


@pytest.fixture()
def stranger():
    return User.objects.create_user("stranger@example.com", "pass-12345")


class TestSquadListView:
    def test_squad_list_renders_200(self, client, squad):
        url = reverse("squads:list")
        response = client.get(url)
        assert response.status_code == 200
        assert squad.name.encode() in response.content

    def test_squad_list_filter_direction(self, client, squad, target_squad):
        url = reverse("squads:list")
        # Фильтруем по Сервисному направлению
        response = client.get(url, {"direction": "сервисное"})
        assert response.status_code == 200
        assert squad.name.encode() in response.content
        assert target_squad.name.encode() not in response.content

    def test_squad_list_filter_recruiting(self, client, squad, target_squad):
        target_squad.is_recruiting = False
        target_squad.save()

        url = reverse("squads:list")
        response = client.get(url, {"recruiting": "1"})
        assert response.status_code == 200
        assert squad.name.encode() in response.content
        assert target_squad.name.encode() not in response.content


class TestSquadDetailView:
    def test_squad_detail_renders_200(self, client, squad):
        url = reverse("squads:detail", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 200
        assert squad.name.encode() in response.content


class TestSquadRevisionView:
    def test_revision_permission_guest_redirects(self, client, squad):
        url = reverse("squads:revision_create", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response["Location"]

    def test_revision_permission_stranger_forbidden(self, client, squad, stranger):
        client.force_login(stranger)
        url = reverse("squads:revision_create", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 403

    def test_revision_permission_commander_can_submit(self, client, squad, commander):
        client.force_login(commander)
        url = reverse("squads:revision_create", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 200

        # Отправка новой ревизии
        post_response = client.post(
            url,
            {
                "motto": "Обновленный девиз",
                "description": "Новый текст",
                "achievements": "2026 — Грант",
                "contact_url": "https://vk.com/sputnik",
                "is_recruiting": True,
            },
        )
        assert post_response.status_code == 302
        assert SquadPageRevision.objects.filter(
            squad=squad, status=SquadPageRevision.Status.PENDING
        ).exists()


class TestSquadTransferView:
    def test_transfer_permission_fighter_forbidden(self, client, squad, fighter):
        # Рядовой боец не может инициировать перевод
        client.force_login(fighter)
        url = reverse("squads:transfer_create", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 403

    def test_transfer_submission_by_commander(
        self, client, squad, target_squad, commander, fighter, pos_fighter
    ):
        client.force_login(commander)
        url = reverse("squads:transfer_create", kwargs={"slug": squad.slug})
        response = client.get(url)
        assert response.status_code == 200

        doc = SimpleUploadedFile(
            "statement.pdf", b"fake pdf content", content_type="application/pdf"
        )
        post_response = client.post(
            url,
            {
                "user": fighter.id,
                "to_squad": target_squad.id,
                "new_position": pos_fighter.id,
                "document": doc,
            },
        )
        assert post_response.status_code == 302
