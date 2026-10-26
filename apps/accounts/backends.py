"""
Кастомный authentication backend.
Нормализует email к нижнему регистру перед поиском пользователя,
чтобы вход через Ivan@Example.COM и ivan@example.com давал одинаковый результат.
"""

from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailCIBackend(ModelBackend):
    """Email-based authentication с нечувствительным к регистру поиском."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(email=username.strip().lower())
        except User.DoesNotExist:
            # Запускаем hasher, чтобы время ответа не давало утечки информации
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
