from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import healthz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("i18n/", include("django.conf.urls.i18n")),
]

# Адреса вида /ru/... и /en/...; корень «/» перенаправляется на язык пользователя.
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("news/", include("apps.news.urls")),
    path("squads/", include("apps.squads.urls")),
    path("vacancies/", include("apps.vacancies.urls")),
    path("requests/", include("apps.requests.urls")),
    path("", include("apps.content.urls")),
    path("", include("apps.core.urls")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
