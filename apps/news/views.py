from django.db.models import Q
from django.views.generic import DetailView, ListView

from apps.accounts.models import Role
from apps.squads.models import Squad

from .models import News


class NewsListView(ListView):
    """Публичная лента событий с фильтрацией и пагинацией."""

    model = News
    paginate_by = 9
    context_object_name = "news_list"

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["news/_news_list_partial.html"]
        return ["news/news_list.html"]

    def get_queryset(self):
        qs = News.objects.published().select_related("squad", "author")

        # Фильтр по категории
        category = self.request.GET.get("category", "").strip()
        if category and category in News.Category.values:
            qs = qs.filter(category=category)

        # Фильтр по организатору
        organizer = self.request.GET.get("organizer", "").strip()
        if organizer and organizer in News.Organizer.values:
            qs = qs.filter(organizer=organizer)

        # Фильтр по отряду
        squad_slug = self.request.GET.get("squad", "").strip()
        if squad_slug:
            qs = qs.filter(squad__slug=squad_slug)

        # Поиск по заголовку и тексту
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(lead__icontains=q) | Q(content__icontains=q))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = News.Category.choices
        context["organizers"] = News.Organizer.choices
        context["squads"] = Squad.objects.all().order_by("name")
        context["current_category"] = self.request.GET.get("category", "")
        context["current_organizer"] = self.request.GET.get("organizer", "")
        context["current_squad"] = self.request.GET.get("squad", "")
        context["current_q"] = self.request.GET.get("q", "")
        return context


class NewsDetailView(DetailView):
    """Детальная страница новости."""

    model = News
    template_name = "news/news_detail.html"
    context_object_name = "news"

    def get_queryset(self):
        # Пользователь видит опубликованные новости, а админы и авторы — и свои черновики
        user = self.request.user
        if user.is_authenticated and (user.is_superuser or user.role in {Role.OWNER, Role.ADMIN}):
            return (
                News.objects.all()
                .select_related("squad", "author")
                .prefetch_related("gallery_images")
            )
        if user.is_authenticated:
            return (
                News.objects.filter(Q(status=News.Status.PUBLISHED) | Q(author=user))
                .select_related("squad", "author")
                .prefetch_related("gallery_images")
            )
        return (
            News.objects.published()
            .select_related("squad", "author")
            .prefetch_related("gallery_images")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_news"] = (
            News.objects.published().exclude(pk=self.object.pk).select_related("squad")[:3]
        )
        return context
