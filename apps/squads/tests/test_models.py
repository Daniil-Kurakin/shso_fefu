import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User
from apps.squads.models import (
    Direction,
    Membership,
    Position,
    Squad,
    SquadPageRevision,
    SquadTransferRequest,
)

pytestmark = pytest.mark.django_db


@pytest.fixture()
def direction():
    return Direction.objects.create(name="Педагогическое", icon="🎓")


@pytest.fixture()
def squad(direction):
    return Squad.objects.create(
        name="СПО «Лав»",
        direction=direction,
        founding_year=2012,
        is_recruiting=True,
    )


@pytest.fixture()
def target_squad(direction):
    return Squad.objects.create(
        name="СПО «Вместе»",
        direction=direction,
        founding_year=2015,
    )


@pytest.fixture()
def fighter():
    return User.objects.create_user("fighter@example.com", "pass-12345", full_name="Иван Боец")


@pytest.fixture()
def commander():
    return User.objects.create_user(
        "commander@example.com", "pass-12345", full_name="Петр Командир"
    )


@pytest.fixture()
def admin_user():
    return User.objects.create_superuser("admin@example.com", "pass-12345")


@pytest.fixture()
def pos_commander():
    return Position.objects.create(
        name="Командир",
        is_staff=True,
        can_initiate_transfer=True,
        order=1,
    )


@pytest.fixture()
def pos_fighter():
    return Position.objects.create(
        name="Боец",
        is_staff=False,
        can_initiate_transfer=False,
        order=5,
    )


def test_direction_creation():
    direction = Direction.objects.create(name="Строительное", icon="🏗️")
    assert direction.slug == "строительное"
    assert str(direction) == "Строительное"


def test_position_creation(pos_commander, pos_fighter):
    assert str(pos_commander) == "Командир (комсостав)"
    assert str(pos_fighter) == "Боец"
    assert pos_commander.can_initiate_transfer is True


def test_single_active_membership_per_user(squad, target_squad, fighter, pos_fighter):
    # Создаем первое активное членство
    Membership.objects.create(
        user=fighter,
        squad=squad,
        position=pos_fighter,
        is_active=True,
    )

    # Второе активное членство для того же пользователя должно вызывать ValidationError
    with pytest.raises(ValidationError):
        Membership.objects.create(
            user=fighter,
            squad=target_squad,
            position=pos_fighter,
            is_active=True,
        )


def test_membership_auto_syncs_user_role(squad, fighter, pos_commander, pos_fighter):
    assert fighter.role == Role.MEMBER

    # Назначение на должность комсостава автоматически обновляет системную роль
    Membership.objects.create(
        user=fighter,
        squad=squad,
        position=pos_commander,
        is_active=True,
    )
    fighter.refresh_from_db()
    assert fighter.role == Role.SQUAD_STAFF


def test_squad_page_revision_publish(squad, admin_user):
    revision = SquadPageRevision.objects.create(
        squad=squad,
        author=admin_user,
        motto="Новый девиз отряда!",
        description="Новое подробное описание",
        achievements="2025 — Победа на конкурсе",
        contact_url="https://vk.com/new_url",
        is_recruiting=False,
    )
    assert revision.status == SquadPageRevision.Status.DRAFT

    revision.publish(moderator=admin_user)

    squad.refresh_from_db()
    assert squad.motto == "Новый девиз отряда!"
    assert squad.description == "Новое подробное описание"
    assert squad.achievements == "2025 — Победа на конкурсе"
    assert squad.contact_url == "https://vk.com/new_url"
    assert squad.is_recruiting is False
    assert revision.status == SquadPageRevision.Status.PUBLISHED


def test_squad_transfer_approve_flow(
    squad, target_squad, fighter, commander, admin_user, pos_fighter
):
    # Начальное членство в исходном отряде
    old_membership = Membership.objects.create(
        user=fighter,
        squad=squad,
        position=pos_fighter,
        is_active=True,
    )

    # Создание заявки на перевод
    transfer = SquadTransferRequest.objects.create(
        user=fighter,
        from_squad=squad,
        to_squad=target_squad,
        new_position=pos_fighter,
        initiator=commander,
        document="transfers/statement.pdf",
    )
    assert transfer.status == SquadTransferRequest.Status.PENDING

    # Подтверждение перевода администратором
    transfer.approve(admin_user=admin_user, comment="Перевод согласован")

    # Проверяем, что старое членство закрыто
    old_membership.refresh_from_db()
    assert old_membership.is_active is False
    assert old_membership.end_date is not None

    # Проверяем, что открыто новое членство в целевом отряде
    new_membership = Membership.objects.get(user=fighter, squad=target_squad, is_active=True)
    assert new_membership.position == pos_fighter

    # Статус заявки обновлен
    transfer.refresh_from_db()
    assert transfer.status == SquadTransferRequest.Status.APPROVED
    assert transfer.decided_by == admin_user


def test_squad_transfer_reject_flow(
    squad, target_squad, fighter, commander, admin_user, pos_fighter
):
    transfer = SquadTransferRequest.objects.create(
        user=fighter,
        from_squad=squad,
        to_squad=target_squad,
        new_position=pos_fighter,
        initiator=commander,
        document="transfers/statement.pdf",
    )
    transfer.reject(admin_user=admin_user, comment="Недостаточно документов")

    transfer.refresh_from_db()
    assert transfer.status == SquadTransferRequest.Status.REJECTED
    assert transfer.decision_comment == "Недостаточно документов"


def test_membership_str_and_clean_without_user():
    membership = Membership()
    # __str__ и clean не должны падать с RelatedObjectDoesNotExist
    assert "—" in str(membership)
    membership.clean()
