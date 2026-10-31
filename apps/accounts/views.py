import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import (
    PortfolioItemForm,
    ProfileSettingsForm,
    RegistrationForm,
    ResendActivationForm,
)
from .models import Role, User, UserPortfolioItem

logger = logging.getLogger(__name__)


def get_client_ip(request: HttpRequest) -> str:
    """Извлечение IP-адреса клиента для аудита согласия по 152-ФЗ."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip or "127.0.0.1"


def send_activation_email(request: HttpRequest, user: User) -> None:
    """Генерация токена и отправка ссылки подтверждения email (149-ФЗ)."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activate_url = request.build_absolute_uri(
        reverse("accounts:activate", kwargs={"uidb64": uid, "token": token})
    )

    subject = (
        render_to_string("accounts/emails/activation_email_subject.txt", {"user": user})
        .replace("\n", "")
        .strip()
    )
    message = render_to_string(
        "accounts/emails/activation_email.txt",
        {
            "user": user,
            "activate_url": activate_url,
        },
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("Письмо с активацией отправлено пользователю %s", user.email)


class RegisterView(FormView):
    """
    Регистрация пользователя на сайте.
    Создает неактивную учетную запись до перехода по ссылке из письма (149-ФЗ),
    фиксирует факт, дату и IP согласия на ОПД (152-ФЗ).
    """

    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:registration_done")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        full_name = form.cleaned_data["full_name"]
        phone = form.cleaned_data.get("phone", "")
        password = form.cleaned_data["password"]

        # Создание неактивного пользователя до подтверждения email
        user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            role=Role.MEMBER,
            is_active=False,
            email_verified=False,
            consent_personal_data=True,
            consent_date=timezone.now(),
            consent_ip=get_client_ip(self.request),
        )
        user.set_password(password)
        user.save()

        # Отправка письма с подтверждением
        send_activation_email(self.request, user)
        self.request.session["registered_email"] = user.email

        return super().form_valid(form)


class RegistrationDoneView(TemplateView):
    """Страница уведомления об отправке письма для активации."""

    template_name = "accounts/registration_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registered_email"] = self.request.session.get("registered_email", "")
        return context


class ActivateView(View):
    """
    Активация учетной записи по токену из письма (149-ФЗ).
    При валидном токене активирует аккаунт и автоматически авторизует пользователя.
    """

    def get(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.email_verified = True
            user.save()
            logger.info("Учётная запись %s успешно активирована", user.email)

            # Автоматический вход в систему
            login(request, user, backend="apps.accounts.backends.EmailCIBackend")
            messages.success(
                request,
                _("Ваш адрес электронной почты успешно подтверждён! Добро пожаловать в ШСО ДВФУ."),
            )
            return redirect("accounts:profile")
        else:
            return render(request, "accounts/activation_invalid.html")


class ResendActivationView(FormView):
    """Повторная отправка письма с активацией, если ссылка утеряна или устарела."""

    template_name = "accounts/resend_activation.html"
    form_class = ResendActivationForm
    success_url = reverse_lazy("accounts:registration_done")

    def form_valid(self, form: ResendActivationForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        user = User.objects.filter(email=email).first()

        if user and not user.email_verified:
            send_activation_email(self.request, user)
            self.request.session["registered_email"] = user.email
            messages.success(
                self.request, _("Ссылка для активации аккаунта отправлена на ваш email.")
            )
        elif user and user.email_verified:
            messages.info(self.request, _("Этот аккаунт уже активирован. Вы можете войти."))
            return redirect("accounts:login")
        else:
            # Не выдаём информацию о наличии/отсутствии чужих email (безопасность)
            messages.success(
                self.request,
                _(
                    "Если указанный email зарегистрирован в системе, "
                    "на него отправлена ссылка для активации."
                ),
            )

        return super().form_valid(form)


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """Выход из системы (POST или GET с подтверждением)."""
    if request.method == "POST":
        logout(request)
        messages.success(request, _("Вы вышли из системы."))
    return redirect("core:home")


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Основная витрина профиля пользователя:
    информация о бойце, членство в отряде, портфолио, история и активность.
    """

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["active_membership"] = (
            user.memberships.filter(is_active=True)
            .select_related("squad__direction", "position")
            .first()
        )
        context["past_memberships"] = (
            user.memberships.filter(is_active=False)
            .select_related("squad__direction", "position")
            .order_by("-start_date")
        )
        context["portfolio_items"] = user.portfolio_items.all()
        context["portfolio_form"] = PortfolioItemForm()
        context["vacancy_applications"] = user.vacancy_applications.select_related(
            "vacancy"
        ).order_by("-id")[:5]
        if user.is_squad_command_staff:
            context["room_bookings"] = user.room_bookings.select_related("room").order_by(
                "-event_date"
            )[:5]
            context["pass_requests"] = user.pass_requests.order_by("-visit_date")[:5]
        else:
            context["room_bookings"] = []
            context["pass_requests"] = []
        context["managed_squads"] = user.get_managed_squads()
        return context

    def post(self, request, *args, **kwargs):
        """Быстрое сохранение данных профиля для совместимости."""
        form = ProfileSettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Профиль успешно сохранён."))
            return redirect("accounts:profile")
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class ProfileSettingsView(LoginRequiredMixin, UpdateView):
    """
    Отдельная страница настроек и редактирования профиля:
    личные данные, контакты, язык, 152-ФЗ аудит, безопасность.
    """

    model = User
    form_class = ProfileSettingsForm
    template_name = "accounts/settings.html"
    success_url = reverse_lazy("accounts:settings")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Настройки профиля успешно сохранены."))
        return super().form_valid(form)


class PortfolioItemCreateView(LoginRequiredMixin, CreateView):
    """Конструктор добавления нового достижения или целины в портфолио."""

    model = UserPortfolioItem
    form_class = PortfolioItemForm
    template_name = "accounts/portfolio_form.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, _("Запись успешно добавлена в ваше портфолио."))
        return super().form_valid(form)


class PortfolioItemUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование записи портфолио."""

    model = UserPortfolioItem
    form_class = PortfolioItemForm
    template_name = "accounts/portfolio_form.html"
    success_url = reverse_lazy("accounts:profile")

    def get_queryset(self):
        return UserPortfolioItem.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("Запись портфолио успешно обновлена."))
        return super().form_valid(form)


class PortfolioItemDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление записи из портфолио."""

    model = UserPortfolioItem
    template_name = "accounts/portfolio_confirm_delete.html"
    success_url = reverse_lazy("accounts:profile")

    def get_queryset(self):
        return UserPortfolioItem.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _("Запись удалена из портфолио."))
        return super().form_valid(form)
