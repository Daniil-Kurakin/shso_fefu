import logging

from django.db import connection
from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.news.models import News
from apps.squads.models import Direction

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_news"] = News.objects.published().select_related("squad")[:3]
        context["directions"] = Direction.objects.all()
        return context


def healthz(request):
    """Проверка доступности для мониторинга и Docker: приложение живо и видит базу."""
    try:
        connection.ensure_connection()
    except Exception:
        logger.exception("healthz: база данных недоступна")
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
