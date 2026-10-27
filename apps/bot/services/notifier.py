import json
import logging
import urllib.request
from django.conf import settings
from apps.bot.models import TelegramProfile

logger = logging.getLogger(__name__)


def send_telegram_raw(chat_id: int, text: str) -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("Ошибка отправки Telegram-сообщения (chat_id=%s): %s", chat_id, e)
        return False


def notify_user_async(user_id: int, text: str):
    """
    Отправка уведомления пользователю.
    Вызывается синхронно или через очередь django-q2.
    """
    try:
        profile = TelegramProfile.objects.filter(
            user_id=user_id,
            is_notifications_enabled=True,
        ).first()
        if profile and profile.chat_id:
            send_telegram_raw(profile.chat_id, text)
    except Exception as e:
        logger.warning("Не удалось отправить уведомление пользователю %s: %s", user_id, e)
