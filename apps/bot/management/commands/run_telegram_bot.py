import base64
import json
import logging
import time
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.bot.models import TelegramLinkToken, TelegramProfile
from apps.bot.services.notifier import send_telegram_raw

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Запуск Telegram-бота в режиме Long Polling (для локальной разработки)"

    def handle(self, *args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN не задан в .env"))
            return

        proxy = getattr(settings, "TELEGRAM_API_PROXY", "").strip()
        handlers = []
        headers = {}
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
            self.stdout.write(f"Используется прокси: {clean_proxy}")

        opener = urllib.request.build_opener(*handlers)

        api_base = getattr(settings, "TELEGRAM_API_URL", "").strip() or "https://api.telegram.org"
        api_base = api_base.rstrip("/")

        self.stdout.write("Удаляем активный Webhook для переключения в режим Polling...")
        try:
            req = urllib.request.Request(
                f"{api_base}/bot{token}/deleteWebhook",
                headers={"User-Agent": "SHSO-FEFU-Notification-Bot/1.0"},
            )
            opener.open(req, timeout=10)
        except Exception as e:
            self.stdout.write(f"Предупреждение при удалении Webhook: {e}")

        self.stdout.write(self.style.SUCCESS("🤖 Бот запущен в режиме polling! Ожидание сообщений..."))
        self.stdout.write("Нажмите Ctrl+C для остановки.")

        offset = 0
        while True:
            try:
                url = f"{api_base}/bot{token}/getUpdates?offset={offset}&timeout=10"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "SHSO-FEFU-Notification-Bot/1.0"},
                )
                with opener.open(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message", {})
                        text = (message.get("text") or "").strip()
                        from_user = message.get("from", {})
                        chat_id = from_user.get("id")

                        if not chat_id:
                            continue

                        self.stdout.write(f"Получено сообщение от {from_user.get('username') or chat_id}: {text}")

                        if text.startswith("/start"):
                            parts = text.split()
                            if len(parts) > 1 and parts[1].startswith("bind_"):
                                token_str = parts[1].replace("bind_", "")
                                token_obj = TelegramLinkToken.objects.filter(token=token_str).first()
                                if token_obj and token_obj.is_valid():
                                    TelegramProfile.objects.update_or_create(
                                        user=token_obj.user,
                                        defaults={
                                            "chat_id": chat_id,
                                            "username": from_user.get("username", ""),
                                            "is_notifications_enabled": True,
                                        },
                                    )
                                    user_name = token_obj.user.get_full_name() or token_obj.user.email
                                    token_obj.delete()
                                    send_telegram_raw(
                                        chat_id,
                                        f"✅ Аккаунт <b>{user_name}</b> успешно привязан!\n\n"
                                        "Теперь вы будете мгновенно получать уведомления об изменении статуса ваших заявок на помещения и пропуска.",
                                    )
                                    self.stdout.write(self.style.SUCCESS(f"Аккаунт {user_name} успешно привязан к chat_id {chat_id}"))
                                else:
                                    send_telegram_raw(
                                        chat_id,
                                        "❌ Ссылка для привязки устарела или недействительна. Пожалуйста, сгенерируйте новую в личном кабинете на сайте.",
                                    )
                            else:
                                send_telegram_raw(
                                    chat_id,
                                    "👋 Привет! Это бот уведомлений Штаба студенческих отрядов ДВФУ.\n\n"
                                    "Чтобы получать уведомления о статусах заявок, привяжите аккаунт в личном кабинете на сайте.",
                                )
            except KeyboardInterrupt:
                self.stdout.write("\nБот остановлен.")
                break
            except Exception as e:
                logger.warning("Polling error: %s", e)
                time.sleep(2)
