import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TelegramProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_profile",
    )
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    is_notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.chat_id})"


class TelegramLinkToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token {self.token} for {self.user}"

    def is_valid(self) -> bool:
        return timezone.now() - self.created_at < timedelta(minutes=15)
