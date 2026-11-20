"""Тесты защитных механизмов: заголовки, валидаторы файлов, XSS-санитайзер, rate-limiting."""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.core.ratelimit import is_rate_limited
from apps.core.sanitizer import sanitize_html
from apps.core.validators import validate_document_file, validate_image_file

pytestmark = pytest.mark.django_db


def test_security_headers_present(client):
    """Каждый ответ содержит современные заголовки безопасности (CSP, Permissions-Policy и др.)."""
    response = client.get("/ru/")
    assert "Content-Security-Policy" in response
    assert "script-src" in response["Content-Security-Policy"]
    assert "Permissions-Policy" in response
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"


def test_sanitize_html_removes_dangerous_tags():
    """XSS-санитайзер вырезает script, iframe и on-обработчики, сохраняя безопасную разметку."""
    raw = (
        '<p>Текст</p><script>alert("xss")</script>'
        '<a href="javascript:alert(1)">Ссылка</a><img src="x" onerror="steal()">'
    )
    cleaned = sanitize_html(raw)
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "onerror" not in cleaned
    assert "javascript:" not in cleaned
    assert "<p>Текст</p>" in cleaned


def test_validate_image_file_valid():
    """Корректный формат и размер изображения проходят валидацию."""
    valid_file = SimpleUploadedFile("avatar.jpg", b"fake_image_bytes", content_type="image/jpeg")
    validate_image_file(valid_file)


def test_validate_image_file_invalid_extension():
    """Опасное расширение отклоняется валидатором изображений."""
    bad_file = SimpleUploadedFile("shell.php", b"<?php phpinfo(); ?>")
    try:
        validate_image_file(bad_file)
        raise AssertionError("Ожидался ValidationError для недопустимого расширения")
    except ValidationError as err:
        assert "Недопустимый формат" in str(err)


def test_validate_image_file_oversized():
    """Изображение больше 5 МБ отклоняется."""
    big_file = SimpleUploadedFile("huge.png", b"0" * (6 * 1024 * 1024))
    try:
        validate_image_file(big_file)
        raise AssertionError("Ожидался ValidationError для файла превышающего 5 МБ")
    except ValidationError as err:
        assert "превышает максимально допустимый" in str(err)


def test_validate_document_file_invalid_extension():
    """Исполняемые файлы (.exe) отклоняются валидатором документов."""
    exe_file = SimpleUploadedFile("malware.exe", b"MZ...")
    try:
        validate_document_file(exe_file)
        raise AssertionError("Ожидался ValidationError для .exe файла")
    except ValidationError as err:
        assert "Недопустимый формат" in str(err)


def test_rate_limiting_exceeded(settings):
    """При превышении допустимого числа попыток срабатывает блокировка."""
    settings.RATELIMIT_ENABLE = True
    test_key = "test_ip_unique_key_123"
    cache.delete(f"ratelimit:{test_key}")
    # Первые 2 попытки разрешены
    assert not is_rate_limited(test_key, max_attempts=2, timeout=60)
    assert not is_rate_limited(test_key, max_attempts=2, timeout=60)
    # 3-я попытка блокируется
    assert is_rate_limited(test_key, max_attempts=2, timeout=60)


def test_login_rate_limiting_view(client, settings):
    """Повторяющиеся POST-запросы на вход блокируются кодом 429."""
    settings.RATELIMIT_ENABLE = True
    login_url = reverse("accounts:login")
    test_ip = "198.51.100.42"
    cache.delete(f"ratelimit:login:{test_ip}")
    extra = {"REMOTE_ADDR": test_ip}

    for _ in range(5):
        client.post(
            login_url,
            {"username": "hack@example.com", "password": "wrong"},
            **extra,
        )
    response = client.post(
        login_url,
        {"username": "hack@example.com", "password": "wrong"},
        **extra,
    )
    assert response.status_code == 429
    cache.delete(f"ratelimit:login:{test_ip}")
    cache.delete("ratelimit:login:127.0.0.1")


def test_non_owner_cannot_access_admin(client, db):
    """Обычный боец не имеет доступа в админ-панель."""
    user = User.objects.create_user("fighter@example.com", "securepass123", role=Role.MEMBER)
    client.force_login(user)
    response = client.get("/ru/admin/", follow=False)
    # Перенаправление на страницу входа админки или отказ в доступе
    assert response.status_code in {302, 403}
