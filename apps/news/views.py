from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.models import Role
from apps.squads.models import Squad

from .forms import NewsForm
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
        user = self.request.user
        can_edit = bool(
            user.is_authenticated
            and (
                user.is_hq_staff
                or (self.object.squad and user.can_manage_squad(self.object.squad))
                or (
                    self.object.author == user
                    and (not self.object.squad or user.can_manage_squad(self.object.squad))
                )
            )
        )
        context["can_edit"] = can_edit
        return context


class NewsCreateView(LoginRequiredMixin, CreateView):
    """Конструктор создания новости со стороны фронтенда."""

    model = News
    form_class = NewsForm
    template_name = "news/news_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_hq_staff or request.user.get_managed_squads().exists()):
            raise PermissionDenied(_("У вас нет прав на создание новостей."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, _("Новость успешно создана!"))
        return super().form_valid(form)


class NewsUpdateView(LoginRequiredMixin, UpdateView):
    """Конструктор редактирования новости."""

    model = News
    form_class = NewsForm
    template_name = "news/news_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        news = self.get_object()
        user = request.user
        can_edit = (
            user.is_hq_staff
            or (news.squad and user.can_manage_squad(news.squad))
            or (news.author == user and (not news.squad or user.can_manage_squad(news.squad)))
        )
        if not can_edit:
            raise PermissionDenied(_("У вас нет прав на редактирование этой новости."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Изменения успешно сохранены!"))
        return super().form_valid(form)
