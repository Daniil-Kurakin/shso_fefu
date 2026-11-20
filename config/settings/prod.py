from .base import *

# Режим отладки строго выключен в продакшене
DEBUG = False

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Не задана переменная окружения DJANGO_ALLOWED_HOSTS")

# Запрет запуска с тестовым/дефолтным секретным ключом
INSECURE_SECRET_KEYS = {
    "dev-only-change-me-please-0123456789abcdef0123456789",
    "test-only-secret-key",
    "ci-only-secret-key",
}
if SECRET_KEY in INSECURE_SECRET_KEYS or len(SECRET_KEY) < 32:
    msg = "В продакшене задан небезопасный или слишком короткий DJANGO_SECRET_KEY!"
    raise ImproperlyConfigured(msg)

# Приложение стоит за Nginx / Cloudflare, который терминирует HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]

# Защита сессий и cookie через HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Заголовки безопасности
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# HSTS (HTTP Strict Transport Security) — 1 год по умолчанию
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Ограничение частоты запросов включено в продакшене
RATELIMIT_ENABLE = env_bool("DJANGO_RATELIMIT_ENABLE", True)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
