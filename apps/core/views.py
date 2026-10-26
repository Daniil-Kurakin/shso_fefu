import logging

from django.db import connection
from django.http import JsonResponse
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = "core/home.html"


def healthz(request):
    """Проверка доступности для мониторинга и Docker: приложение живо и видит базу."""
    try:
        connection.ensure_connection()
    except Exception:
        logger.exception("healthz: база данных недоступна")
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
