import logging

from django.core.cache import cache
from django.db import DatabaseError

from .models import SiteSetting

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "students_count": "900+",
    "squads_count": "22",
    "directions_count": "6",
    "work_semester_year": "2026",
    "hq_office": "о. Русский, Кампус ДВФУ, корпус А, уровень 8, ауд. А826",
    "hq_email": "shso@dvfu.ru",
    "hq_vk": "https://vk.com/shso_fefu",
    "hq_telegram": "https://t.me/fefudvfu",
    "stats_source": "Александр Кайданович, старт трудового семестра 2026",
}


def site_settings(request):
    """
    Контекстный процессор для доступа к глобальным настройкам и контактам сайта.
    Результат кэшируется на 10 минут.
    """
    lang = getattr(request, "LANGUAGE_CODE", "ru")
    cache_key = f"context_site_settings_{lang}"
    settings_dict = cache.get(cache_key)

    if settings_dict is None:
        settings_dict = dict(DEFAULT_SETTINGS)
        try:
            for s in SiteSetting.objects.all():
                val = s.value_en if lang == "en" and s.value_en else s.value
                settings_dict[s.key] = val
                if s.year:
                    settings_dict[f"{s.key}_year"] = s.year
                if s.source:
                    settings_dict[f"{s.key}_source"] = s.source
        except DatabaseError:
            # База данных ещё не содержит таблицу на стадии первичных миграций
            logger.debug("SiteSetting table not ready yet")
        cache.set(cache_key, settings_dict, timeout=600)

    return {"site_settings": settings_dict}
