import base64
import json
import logging
import urllib.parse
import urllib.request
from django.conf import settings
from apps.bot.models import TelegramProfile

logger = logging.getLogger(__name__)


def send_telegram_raw(chat_id: int | str, text: str) -> bool:
    """Прямая отправка сообщения через Telegram Bot API."""
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or not chat_id:
        logger.warning("Telegram send skipped: token=%s, chat_id=%s", bool(token), chat_id)
        return False

    api_base = getattr(settings, "TELEGRAM_API_URL", "").strip() or "https://api.telegram.org"
    url = f"{api_base.rstrip('/')}/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    handlers = []
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SHSO-FEFU-Notification-Bot/1.0 (Windows; Python 3.12)",
    }
    proxy = getattr(settings, "TELEGRAM_API_PROXY", "").strip()
    if proxy:
        parsed = urllib.parse.urlsplit(proxy)
        if parsed.username and parsed.password:
            user_pass = f"{parsed.username}:{parsed.password}".encode("utf-8")
            auth_b64 = base64.b64encode(user_pass).decode("ascii")
            headers["Proxy-Authorization"] = f"Basic {auth_b64}"
            clean_proxy = (
                f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                if parsed.port
                else f"{parsed.scheme}://{parsed.hostname}"
            )
        else:
            clean_proxy = proxy
        handlers.append(urllib.request.ProxyHandler({"http": clean_proxy, "https": clean_proxy}))

    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
    )

    try:
        with opener.open(req, timeout=12) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("Ошибка отправки Telegram-сообщения (chat_id=%s): %s", chat_id, e)
        return False


def notify_user_async(user_id: int, text: str):
    """
    Отправка уведомления пользователю.
    Если доступен django-q, выполняется в фоновом воркере, иначе синхронно.
    """
    try:
        from django_q.tasks import async_task
        async_task("apps.bot.services.notifier._deliver_notification", user_id, text)
    except Exception:
        _deliver_notification(user_id, text)


def _deliver_notification(user_id: int, text: str):
    try:
        profile = TelegramProfile.objects.filter(
            user_id=user_id,
            is_notifications_enabled=True,
        ).first()
        if profile and profile.chat_id:
            send_telegram_raw(profile.chat_id, text)
        else:
            logger.info("У пользователя %s нет привязанного Telegram-профиля", user_id)
    except Exception as e:
        logger.warning("Не удалось доставить уведомление пользователю %s: %s", user_id, e)
