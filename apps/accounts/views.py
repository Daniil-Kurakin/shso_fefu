import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import UpdateView

from .models import User

logger = logging.getLogger(__name__)


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    """Выход из системы (POST или GET с подтверждением)."""
    if request.method == "POST":
        logout(request)
        messages.success(request, _("Вы вышли из системы."))
    return redirect("core:home")


class ProfileView(LoginRequiredMixin, UpdateView):
    """Страница профиля: редактирование имени, подписи и языка интерфейса."""

    model = User
    fields = ["full_name", "signature", "language"]
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Профиль успешно сохранён."))
        return super().form_valid(form)
