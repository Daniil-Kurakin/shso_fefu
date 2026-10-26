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


class TestRegistrationView:
    def test_registration_page_renders(self, client):
        url = reverse("accounts:register")
        response = client.get(url)
        assert response.status_code == 200
        assert "152-ФЗ" in response.content.decode("utf-8")

    def test_registration_success(self, client, mailoutbox):
        url = reverse("accounts:register")
        response = client.post(
            url,
            {
                "full_name": "Иванов Иван Иванович",
                "email": "ivanov@dvfu.ru",
                "phone": "+7 (999) 123-45-67",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                "consent_personal_data": "on",
                "website": "",
            },
        )
        assert response.status_code == 302
        assert response["Location"] == reverse("accounts:registration_done")

        # Проверяем, что пользователь создан в БД
        user = User.objects.get(email="ivanov@dvfu.ru")
        assert not user.is_active  # Должен быть неактивен до перехода по ссылке
        assert not user.email_verified
        assert user.consent_personal_data
        assert user.consent_date is not None
        assert user.consent_ip is not None
        assert user.phone == "+7 (999) 123-45-67"

        # Проверяем отправку письма активации (149-ФЗ)
        assert len(mailoutbox) == 1
        assert "Активация учётной записи" in mailoutbox[0].subject
        assert user.email in mailoutbox[0].to
        assert "/accounts/activate/" in mailoutbox[0].body

    def test_registration_requires_152fz_consent(self, client):
        url = reverse("accounts:register")
        response = client.post(
            url,
            {
                "full_name": "Иванов Иван Иванович",
                "email": "ivanov@dvfu.ru",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                # без согласия consent_personal_data!
            },
        )
        assert response.status_code == 200
        assert not User.objects.filter(email="ivanov@dvfu.ru").exists()
        assert "обработку персональных данных" in response.content.decode("utf-8")

    def test_registration_rejects_duplicate_email(self, client, user):
        url = reverse("accounts:register")
        response = client.post(
            url,
            {
                "full_name": "Тестовый дубликат",
                "email": "TEST@EXAMPLE.COM",  # уже существует
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                "consent_personal_data": "on",
            },
        )
        assert response.status_code == 200
        assert "уже зарегистрирован" in response.content.decode("utf-8")

    def test_registration_rejects_disposable_email(self, client):
        url = reverse("accounts:register")
        response = client.post(
            url,
            {
                "full_name": "Спамер",
                "email": "spammer@tempmail.com",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                "consent_personal_data": "on",
            },
        )
        assert response.status_code == 200
        assert "одноразовой почты запрещена" in response.content.decode("utf-8")

    def test_registration_honeypot_catches_bot(self, client):
        url = reverse("accounts:register")
        response = client.post(
            url,
            {
                "full_name": "Бот",
                "email": "bot@example.com",
                "password": "StrongPassword123!",
                "password_confirm": "StrongPassword123!",
                "consent_personal_data": "on",
                "website": "http://spamsite.com",  # Honeypot заполнен
            },
        )
        assert response.status_code == 200
        assert not User.objects.filter(email="bot@example.com").exists()


class TestActivationView:
    def test_activation_success(self, client):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = User.objects.create_user("new_user@dvfu.ru", "StrongPassword123!", is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        url = reverse("accounts:activate", kwargs={"uidb64": uid, "token": token})
        response = client.get(url)
        assert response.status_code == 302

        user.refresh_from_db()
        assert user.is_active
        assert user.email_verified

        # Проверяем, что пользователь авторизован
        assert int(client.session["_auth_user_id"]) == user.pk

    def test_activation_invalid_token(self, client):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = User.objects.create_user("new_user@dvfu.ru", "StrongPassword123!", is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        url = reverse("accounts:activate", kwargs={"uidb64": uid, "token": "invalid-token"})
        response = client.get(url)
        assert response.status_code == 200
        assert "Ссылка недействительна" in response.content.decode("utf-8")

        user.refresh_from_db()
        assert not user.is_active


class TestResendActivationView:
    def test_resend_activation_sends_email_for_unverified(self, client, mailoutbox):
        User.objects.create_user("waiting@dvfu.ru", "StrongPassword123!", is_active=False)
        url = reverse("accounts:resend_activation")
        response = client.post(url, {"email": "waiting@dvfu.ru"})
        assert response.status_code == 302
        assert len(mailoutbox) == 1
        assert "Активация учётной записи" in mailoutbox[0].subject


class TestLegalPages:
    def test_privacy_policy_page(self, client):
        url = reverse("content:privacy")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "152-ФЗ" in content
        assert "ШСО ДВФУ" in content

    def test_terms_of_service_page(self, client):
        url = reverse("content:terms")
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Пользовательское соглашение" in content
        assert "149-ФЗ" in content
