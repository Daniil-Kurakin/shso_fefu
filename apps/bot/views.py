import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.bot.models import TelegramLinkToken, TelegramProfile
from apps.bot.services.notifier import send_telegram_raw

logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    """Приём входящих событий от Telegram Bot API."""
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
                    "❌ Ссылка для привязки устарела или недействительна. "
                    "Пожалуйста, сгенерируйте новую в личном кабинете на сайте.",
                )
        else:
            send_telegram_raw(
                chat_id,
                "👋 Привет! Это бот уведомлений Штаба студенческих отрядов ДВФУ.\n\n"
                "Чтобы привязать аккаунт, перейдите в личный кабинет на сайте "
                "и нажмите «Подключить Telegram».",
            )

    return HttpResponse("OK")


@login_required
def connect_telegram(request):
    """Генерация одноразовой ссылки и редирект в бота."""
    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "shso_fefu_bot"
    token = TelegramLinkToken.objects.create(user=request.user)
    bot_url = f"https://t.me/{bot_username}?start=bind_{token.token}"
    return redirect(bot_url)


@login_required
@require_POST
def disconnect_telegram(request):
    """Отвязка Telegram от профиля."""
    TelegramProfile.objects.filter(user=request.user).delete()
    messages.info(request, _("Telegram-уведомления успешно отключены."))
    return redirect("accounts:settings")


@login_required
@require_POST
def bind_telegram_manual(request):
    """
    Ручная привязка Telegram по chat_id / username.
    Позволяет привязать Telegram локально без внешнего Webhook.
    """
    raw_chat_id = request.POST.get("chat_id", "").strip()
    username = request.POST.get("username", "").strip().lstrip("@")

    if not raw_chat_id:
        messages.error(request, _("Пожалуйста, укажите ваш Telegram Chat ID."))
        return redirect("accounts:settings")

    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        messages.error(request, _("Chat ID должен состоять только из цифр."))
        return redirect("accounts:settings")

    profile, _created = TelegramProfile.objects.update_or_create(
        user=request.user,
        defaults={
            "chat_id": chat_id,
            "username": username,
            "is_notifications_enabled": True,
        },
    )

    # Пробуем отправить приветственное тестовое сообщение
    sent = send_telegram_raw(
        chat_id,
        f"✅ <b>Telegram успешно привязан!</b>\n\n"
        f"Пользователь: <b>{request.user.get_full_name()}</b>\n"
        f"Уведомления о статусе бронирований и пропусков активны.",
    )

    if sent:
        messages.success(
            request, _("Telegram успешно привязан! Вам отправлено тестовое сообщение в бота.")
        )
    else:
        messages.warning(
            request,
            _(
                "Telegram ID сохранён, но тестовое сообщение не дошло. "
                "Убедитесь, что вы нажали «Запустить» (/start) в диалоге с ботом."
            ),
        )

    return redirect("accounts:settings")


@login_required
def test_send_telegram(request):
    """Тестовая отправка уведомления текущему пользователю."""
    profile = getattr(request.user, "telegram_profile", None)
    if not profile or not profile.chat_id:
        messages.error(request, _("Сначала привяжите Telegram-аккаунт."))
        return redirect("accounts:settings")

    name = request.user.get_short_name()
    sent = send_telegram_raw(
        profile.chat_id,
        f"🔔 <b>Тестовое уведомление ШСО ДВФУ</b>\n\n"
        f"Привет, {name}! Бот успешно подключен и готов присылать уведомления.",
    )
    if sent:
        messages.success(request, _("Тестовое сообщение успешно отправлено в Telegram!"))
    else:
        messages.error(
            request,
            _(
                "Не удалось доставить сообщение. "
                "Проверьте, не заблокирован ли бот, и правильность токена в .env."
            ),
        )

    return redirect("accounts:settings")
