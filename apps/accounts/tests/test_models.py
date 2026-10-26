import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User, UserPortfolioItem

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email_and_sets_default_role():
    user = User.objects.create_user("Ivan@Example.COM", "pass-12345-xyz")
    assert user.email == "ivan@example.com"
    assert user.role == Role.MEMBER
    assert not user.is_staff
    assert user.check_password("pass-12345-xyz")


def test_create_superuser_is_owner():
    user = User.objects.create_superuser("boss@example.com", "pass-12345-xyz")
    assert user.is_staff and user.is_superuser
    assert user.role == Role.OWNER
    assert user.email_verified
    assert user.consent_personal_data
    assert user.consent_date is not None


def test_email_is_unique_case_insensitively():
    User.objects.create_user("a@example.com", "pass-12345-xyz")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("A@example.com", "pass-12345-xyz")


def test_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user("", "pass-12345-xyz")


def test_user_initials_and_avatar():
    user = User.objects.create_user("test@example.com", "pass-12345-xyz", full_name="Иванов Иван")
    assert user.get_initials() == "ИИ"
    assert user.get_avatar_url() is None

    user_no_name = User.objects.create_user("petrov@example.com", "pass-12345-xyz")
    assert user_no_name.get_initials() == "P"


def test_user_portfolio_item_str_and_creation():
    user = User.objects.create_user(
        "fighter@example.com", "pass-12345-xyz", full_name="Сидоров Сидор"
    )
    item = UserPortfolioItem.objects.create(
        user=user,
        title="Целина 2025: ВДЦ Океан",
        category=UserPortfolioItem.Category.CELINA,
        year=2025,
        organization="ВДЦ «Океан»",
    )
    assert "Целина 2025: ВДЦ Океан" in str(item)
    assert "Сидоров Сидор" in str(item)
    assert item.user == user
