"""Утилиты ограничения частоты запросов (Rate Limiting) на базе кэша Django."""

import functools
import logging
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """Извлечение реального IP-адреса клиента с учётом обратного прокси."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip or "127.0.0.1"


def is_rate_limited(
    key: str,
    max_attempts: int = 5,
    timeout: int = 300,
    increment: bool = True,
) -> bool:
    """
    Проверяет, превышен ли лимит попыток.
    Возвращает True, если лимит превышен (запрос блокируется).
    """
    cache_key = f"ratelimit:{key}"
    if not getattr(settings, "RATELIMIT_ENABLE", True):
        return False
    try:
        current = cache.get(cache_key, 0)
        if current >= max_attempts:
            return True
        if increment:
            try:
                # Атомарный инкремент, если ключ существует
                added = cache.add(cache_key, 1, timeout=timeout)
                if not added:
                    cache.incr(cache_key)
            except Exception:
                cache.set(cache_key, current + 1, timeout=timeout)
        return False
    except Exception as exc:
        logger.warning("Ошибка проверки rate limit: %s", exc)
        return False


def rate_limit(
    key_prefix: str = "general",
    max_attempts: int = 10,
    timeout: int = 300,
    methods: tuple[str, ...] = ("POST",),
) -> Callable:
    """
    Декоратор ограничения частоты запросов для представлений.
    При превышении лимита возвращает ответ с кодом 429 Too Many Requests.
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request.method in methods:
                ip = get_client_ip(request)
                rate_key = f"{key_prefix}:{ip}"
                if is_rate_limited(rate_key, max_attempts=max_attempts, timeout=timeout):
                    logger.warning("Rate limit exceeded for IP %s on %s", ip, request.path)
                    msg = str(
                        _(
                            "Слишком много запросов. В целях безопасности доступ временно "
                            "ограничен. Пожалуйста, подождите несколько минут."
                        )
                    )
                    return HttpResponse(msg, status=429, content_type="text/plain; charset=utf-8")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
