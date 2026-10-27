import json
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from apps.bot.models import TelegramLinkToken, TelegramProfile
from apps.bot.services.notifier import send_telegram_raw

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponse("Invalid JSON", status=400)

    message = data.get("message", {})
    text = (message.get("text") or "").strip()
    from_user = message.get("from", {})
    chat_id = from_user.get("id")

    if not chat_id:
        return HttpResponse("OK")

    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1 and parts[1].startswith("bind_"):
            token_str = parts[1].replace("bind_", "")
            token = TelegramLinkToken.objects.filter(token=token_str).first()
            if token and token.is_valid():
                TelegramProfile.objects.update_or_create(
                    user=token.user,
                    defaults={
                        "chat_id": chat_id,
                        "username": from_user.get("username", ""),
                        "is_notifications_enabled": True,
                    },
                )
                user_name = token.user.get_full_name() or token.user.email
                token.delete()
                send_telegram_raw(
                    chat_id,
                    f"✅ Аккаунт <b>{user_name}</b> успешно привязан!\n\n"
                    "Теперь вы будете получать уведомления об изменении статуса ваших заявок.",
                )
            else:
                send_telegram_raw(
                    chat_id,
                    "❌ Ссылка для привязки устарела или недействительна. Сгенерируйте новую в личном кабинете на сайте.",
                )
        else:
            send_telegram_raw(
                chat_id,
                "👋 Привет! Это бот уведомлений Штаба студенческих отрядов ДВФУ.\n\n"
                "Чтобы привязать аккаунт, перейдите в личный кабинет на сайте и нажмите кнопку «Подключить Telegram».",
            )

    return HttpResponse("OK")
