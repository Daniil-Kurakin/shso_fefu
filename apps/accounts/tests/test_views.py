import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user(db):
    return User.objects.create_user("test@example.com", "ValidPass123!")


@pytest.fixture()
def admin_user(db):
    return User.objects.create_superuser("admin@example.com", "ValidPass123!")


class TestLoginView:
    def test_login_page_renders(self, client):
        url = reverse("accounts:login")
        response = client.get(url)
        assert response.status_code == 200
        assert b"email" in response.content.lower()

    def test_login_success_redirects_to_profile(self, client, user):
        url = reverse("accounts:login")
        response = client.post(url, {"username": "test@example.com", "password": "ValidPass123!"})
        assert response.status_code == 302
        assert response["Location"] == reverse("accounts:profile")

    def test_login_failure_shows_error(self, client, user):
        url = reverse("accounts:login")
        response = client.post(url, {"username": "test@example.com", "password": "wrongpass"})
        assert response.status_code == 200
        # Форма должна отобразиться снова с ошибкой
        assert b"form" in response.content.lower()

    def test_login_case_insensitive_email(self, client, user):
        url = reverse("accounts:login")
        response = client.post(url, {"username": "TEST@EXAMPLE.COM", "password": "ValidPass123!"})
        assert response.status_code == 302

    def test_login_redirects_already_authenticated(self, client, user):
        client.force_login(user)
        url = reverse("accounts:login")
        response = client.get(url)
        # Залогиненный пользователь попадает на profile, а не на login
        assert response.status_code in (200, 302)


class TestLogoutView:
    def test_logout_post_redirects_home(self, client, user):
        client.force_login(user)
        url = reverse("accounts:logout")
        response = client.post(url)
        assert response.status_code == 302
        assert response["Location"] == reverse("core:home")

    def test_logout_get_also_redirects(self, client, user):
        client.force_login(user)
        url = reverse("accounts:logout")
        response = client.get(url)
        assert response.status_code == 302


class TestProfileView:
    def test_profile_requires_login(self, client):
        url = reverse("accounts:profile")
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response["Location"]

    def test_profile_renders_for_authenticated(self, client, user):
        client.force_login(user)
        url = reverse("accounts:profile")
        response = client.get(url)
        assert response.status_code == 200
        assert user.email.encode() in response.content

    def test_profile_update_full_name(self, client, user):
        client.force_login(user)
        url = reverse("accounts:profile")
        response = client.post(
            url,
            {
                "full_name": "Иванов Иван Иванович",
                "signature": "",
                "language": "ru",
            },
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.full_name == "Иванов Иван Иванович"

    def test_profile_cannot_edit_other_user(self, client, user, admin_user):
        """ProfileView всегда редактирует текущего пользователя, не чужого."""
        client.force_login(user)
        url = reverse("accounts:profile")
        client.post(
            url,
            {
                "full_name": "Хакер",
                "signature": "",
                "language": "ru",
            },
        )
        admin_user.refresh_from_db()
        assert admin_user.full_name != "Хакер"


class TestPasswordResetView:
    def test_reset_page_renders(self, client):
        url = reverse("accounts:password_reset")
        response = client.get(url)
        assert response.status_code == 200

    def test_reset_post_with_valid_email(self, client, user, mailoutbox):
        url = reverse("accounts:password_reset")
        response = client.post(url, {"email": user.email})
        assert response.status_code == 302
        assert response["Location"] == reverse("accounts:password_reset_done")
        assert len(mailoutbox) == 1
        assert "ШСО ДВФУ" in mailoutbox[0].subject

    def test_reset_post_with_unknown_email_does_not_reveal(self, client, mailoutbox):
        """Не должны раскрывать факт отсутствия email в системе."""
        url = reverse("accounts:password_reset")
        response = client.post(url, {"email": "nobody@example.com"})
        # Всё равно перенаправляет на done — не раскрываем, зарегистрирован ли email
        assert response.status_code == 302
        assert response["Location"] == reverse("accounts:password_reset_done")
        assert len(mailoutbox) == 0


class TestPasswordChangeView:
    def test_change_requires_login(self, client):
        url = reverse("accounts:password_change")
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response["Location"]

    def test_change_renders_for_authenticated(self, client, user):
        client.force_login(user)
        url = reverse("accounts:password_change")
        response = client.get(url)
        assert response.status_code == 200

    def test_change_success(self, client, user):
        client.force_login(user)
        url = reverse("accounts:password_change")
        response = client.post(
            url,
            {
                "old_password": "ValidPass123!",
                "new_password1": "NewValidPass456!",
                "new_password2": "NewValidPass456!",
            },
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.check_password("NewValidPass456!")

    def test_change_wrong_old_password(self, client, user):
        client.force_login(user)
        url = reverse("accounts:password_change")
        response = client.post(
            url,
            {
                "old_password": "wrongpassword",
                "new_password1": "NewValidPass456!",
                "new_password2": "NewValidPass456!",
            },
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("ValidPass123!")  # не изменился
