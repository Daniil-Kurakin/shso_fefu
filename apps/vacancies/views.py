from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormMixin

from .forms import VacancyApplicationForm, VacancyForm
from .models import Vacancy, VacancyApplication


class VacancyListView(ListView):
    """Каталог вакансий и направлений набора."""

    model = Vacancy
    template_name = "vacancies/vacancy_list.html"
    context_object_name = "vacancies"
    ordering = ["-type", "-created_at"]

    def get_queryset(self):
        qs = Vacancy.objects.open().select_related("squad")

        # Фильтр по типу вакансии
        v_type = self.request.GET.get("type", "").strip()
        if v_type in Vacancy.Type.values:
            qs = qs.filter(type=v_type)

        # Поиск по названию и описанию
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(requirements__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["types"] = Vacancy.Type.choices
        context["current_type"] = self.request.GET.get("type", "")
        context["current_q"] = self.request.GET.get("q", "")
        return context


class VacancyDetailView(FormMixin, DetailView):
    """Детальная страница вакансии с формой отклика."""

    model = Vacancy
    template_name = "vacancies/vacancy_detail.html"
    context_object_name = "vacancy"
    form_class = VacancyApplicationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["vacancy"] = self.object
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        can_edit = bool(
            user.is_authenticated
            and (
                user.is_hq_staff or (self.object.squad and user.can_manage_squad(self.object.squad))
            )
        )
        context["can_edit"] = can_edit
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_accepting_applications:
            messages.error(request, _("Приём откликов на данную вакансию уже завершён."))
            return redirect(self.object.get_absolute_url())

        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        application = form.save(commit=False)
        application.vacancy = self.object
        if self.request.user.is_authenticated:
            application.user = self.request.user
        application.status = VacancyApplication.Status.NEW
        application.save()

        messages.success(
            self.request,
            _(
                "Ваш отклик успешно принят! "
                "Руководство штаба свяжется с вами по указанному контакту."
            ),
        )
        return redirect(self.object.get_absolute_url())


class VacancyCreateView(LoginRequiredMixin, CreateView):
    """Конструктор создания вакансии / набора со стороны фронтенда."""

    model = Vacancy
    form_class = VacancyForm
    template_name = "vacancies/vacancy_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_hq_staff or request.user.get_managed_squads().exists()):
            raise PermissionDenied(_("У вас нет прав на создание вакансий."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Вакансия успешно создана!"))
        return super().form_valid(form)


class VacancyUpdateView(LoginRequiredMixin, UpdateView):
    """Конструктор редактирования вакансии."""

    model = Vacancy
    form_class = VacancyForm
    template_name = "vacancies/vacancy_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        vacancy = self.get_object()
        user = request.user
        can_edit = user.is_hq_staff or user.can_manage_squad(vacancy.squad)
        if not can_edit:
            raise PermissionDenied(_("У вас нет прав на редактирование этой вакансии."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Вакансия успешно обновлена!"))
        return super().form_valid(form)
