import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User

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
