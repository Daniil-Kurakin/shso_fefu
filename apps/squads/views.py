from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, FormView, ListView

from apps.news.models import News

from .forms import (
    SquadForm,
    SquadMemberAddForm,
    SquadPageRevisionForm,
    SquadTransferRequestForm,
)
from .models import Direction, Membership, Squad, SquadPageRevision, SquadTransferRequest


def user_can_edit_squad(user, squad: Squad) -> bool:
    """Проверяет право пользователя редактировать страницу данного отряда."""
    if not user.is_authenticated:
        return False
    if user.is_hq_staff:
        return True
    return Membership.objects.filter(
        user=user,
        squad=squad,
        is_active=True,
        position__is_staff=True,
    ).exists()


def user_can_transfer_squad(user, squad: Squad) -> bool:
    """Проверяет право пользователя инициировать переход из данного отряда (командир)."""
    if not user.is_authenticated:
        return False
    if user.is_hq_staff:
        return True
    return Membership.objects.filter(
        user=user,
        squad=squad,
        is_active=True,
        position__can_initiate_transfer=True,
    ).exists()


class SquadListView(ListView):
    """Каталог отрядов ШСО ДВФУ с фильтром по направлениям и набору."""

    model = Squad
    template_name = "squads/squad_list.html"
    context_object_name = "squads"
    ordering = ["direction__order", "name"]

    def get_queryset(self):
        qs = Squad.objects.select_related("direction").prefetch_related("memberships")

        # Фильтр по направлению
        direction_slug = self.request.GET.get("direction", "").strip()
        if direction_slug:
            qs = qs.filter(direction__slug=direction_slug)

        # Фильтр по открытому набору
        if self.request.GET.get("recruiting") == "1":
            qs = qs.filter(is_recruiting=True)

        # Поиск по названию, девизу
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(motto__icontains=q) | Q(description__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["directions"] = Direction.objects.all()
        context["current_direction"] = self.request.GET.get("direction", "")
        context["current_recruiting"] = self.request.GET.get("recruiting", "")
        context["current_q"] = self.request.GET.get("q", "")
        return context


class SquadDetailView(DetailView):
    """Публичная страница отряда."""

    model = Squad
    template_name = "squads/squad_detail.html"
    context_object_name = "squad"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        squad = self.object

        # Активный состав отряда
        active_memberships = (
            squad.memberships.filter(is_active=True)
            .select_related("user", "position")
            .order_by("position__order", "user__full_name")
        )
        context["commanders"] = [m for m in active_memberships if m.position.is_staff]
        context["fighters"] = [m for m in active_memberships if not m.position.is_staff]

        # Новости данного отряда
        context["squad_news"] = News.objects.published().filter(squad=squad)[:4]

        # Права пользователя на редактирование и переходы
        user = self.request.user
        context["can_edit"] = user_can_edit_squad(user, squad)
        context["can_transfer"] = user_can_transfer_squad(user, squad)
        return context


class SquadRevisionCreateView(LoginRequiredMixin, CreateView):
    """Создание новой ревизии страницы отряда комсоставом."""

    model = SquadPageRevision
    form_class = SquadPageRevisionForm
    template_name = "squads/revision_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.squad = get_object_or_404(Squad, slug=self.kwargs["slug"])
        if not user_can_edit_squad(request.user, self.squad):
            raise PermissionDenied(_("Редактировать страницу отряда может только его комсостав."))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "motto": self.squad.motto,
                "description": self.squad.description,
                "achievements": self.squad.achievements,
                "contact_url": self.squad.contact_url,
                "is_recruiting": self.squad.is_recruiting,
            }
        )
        return initial

    def form_valid(self, form):
        revision = form.save(commit=False)
        revision.squad = self.squad
        revision.author = self.request.user
        revision.status = SquadPageRevision.Status.PENDING
        revision.save()
        messages.success(
            self.request,
            _("Изменения отправлены на согласование. После проверки они появятся на сайте."),
        )
        return redirect(self.squad.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["squad"] = self.squad
        return context


class SquadTransferCreateView(LoginRequiredMixin, CreateView):
    """Подача заявки на перевод бойца командиром отряда."""

    model = SquadTransferRequest
    form_class = SquadTransferRequestForm
    template_name = "squads/transfer_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.squad = get_object_or_404(Squad, slug=self.kwargs["slug"])
        if not user_can_transfer_squad(request.user, self.squad):
            raise PermissionDenied(_("Инициировать перевод бойца может только командир отряда."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["from_squad"] = self.squad
        return kwargs

    def form_valid(self, form):
        transfer = form.save(commit=False)
        transfer.from_squad = self.squad
        transfer.initiator = self.request.user
        transfer.status = SquadTransferRequest.Status.PENDING
        transfer.save()
        messages.success(
            self.request,
            _("Заявка на перевод бойца передана на рассмотрение руководству штаба."),
        )
        return redirect(self.squad.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["squad"] = self.squad
        return context


class SquadCreateView(LoginRequiredMixin, CreateView):
    """Конструктор создания нового студенческого отряда (только руководство штаба)."""

    model = Squad
    form_class = SquadForm
    template_name = "squads/squad_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_hq_staff:
            raise PermissionDenied(_("Создавать новые отряды может только руководство штаба."))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        squad = form.save()
        messages.success(
            self.request,
            _("Отряд «%(name)s» успешно создан!") % {"name": squad.name},
        )
        return redirect(squad.get_absolute_url())


class SquadMemberAddView(LoginRequiredMixin, FormView):
    """Конструктор добавления бойца в отряд комсоставом или штабом."""

    form_class = SquadMemberAddForm
    template_name = "squads/squad_member_add.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.squad = get_object_or_404(Squad, slug=self.kwargs["slug"])
        if not request.user.can_manage_squad(self.squad):
            raise PermissionDenied(_("Добавлять бойцов может только комсостав отряда или штаб."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["squad"] = self.squad
        return kwargs

    def form_valid(self, form):
        membership = form.save(commit=False)
        membership.squad = self.squad
        membership.save()
        name = membership.user.get_full_name() or membership.user.username
        messages.success(
            self.request,
            _("Боец %(name)s успешно добавлен в состав отряда!") % {"name": name},
        )
        return redirect(self.squad.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["squad"] = self.squad
        return context
