from django.urls import path
from apps.bot import views

app_name = "bot"

urlpatterns = [
    path("webhook/", views.telegram_webhook, name="webhook"),
    path("connect/", views.connect_telegram, name="connect"),
    path("disconnect/", views.disconnect_telegram, name="disconnect"),
    path("bind-manual/", views.bind_telegram_manual, name="bind_manual"),
    path("test-send/", views.test_send_telegram, name="test_send"),
]
