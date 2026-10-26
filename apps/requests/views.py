from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView

from .forms import PassRequestForm, PassVisitorFormSet, RoomBookingRequestForm
from .models import PassRequest, RoomBookingRequest


class UserRequestDashboardView(LoginRequiredMixin, TemplateView):
    """Личный кабинет заявителя со всеми поданными заявками."""

    template_name = "requests/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tab = self.request.GET.get("tab", "all")

        room_bookings = (
            RoomBookingRequest.objects.filter(user=user)
            .select_related("room", "squad")
            .order_by("-created_at")
        )
        pass_requests = (
            PassRequest.objects.filter(user=user)
            .select_related("squad")
            .prefetch_related("visitors")
            .order_by("-created_at")
        )

        context["tab"] = tab
        context["room_bookings"] = room_bookings
        context["pass_requests"] = pass_requests
        context["pending_count"] = (
            room_bookings.filter(status=RoomBookingRequest.Status.SUBMITTED).count()
            + pass_requests.filter(status=PassRequest.Status.SUBMITTED).count()
        )
        return context


class RoomBookingCreateView(LoginRequiredMixin, CreateView):
    """Подача заявки на бронирование аудитории / зала."""

    model = RoomBookingRequest
    form_class = RoomBookingRequestForm
    template_name = "requests/room_booking_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        booking = form.save(commit=False)
        booking.user = self.request.user
        booking.status = RoomBookingRequest.Status.SUBMITTED
        booking.save()

        messages.success(
            self.request,
            _(
                f"Заявка на бронирование «{booking.room.name}» "
                "успешно отправлена на рассмотрение штаба!"
            ),
        )
        return redirect(booking.get_absolute_url())


class RoomBookingDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Просмотр статуса заявки на помещение."""

    model = RoomBookingRequest
    template_name = "requests/room_booking_detail.html"
    context_object_name = "booking"

    def test_func(self):
        obj = self.get_object()
        return self.request.user.is_staff or obj.user == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["conflicting_bookings"] = self.object.get_conflicting_bookings()
        return context


class RoomBookingCancelView(LoginRequiredMixin, View):
    """Отмена заявки заявителем."""

    def post(self, request, pk):
        booking = get_object_or_404(RoomBookingRequest, pk=pk)
        if booking.user != request.user and not request.user.is_staff:
            raise PermissionDenied

        if booking.status in [
            RoomBookingRequest.Status.APPROVED,
            RoomBookingRequest.Status.SUBMITTED,
        ]:
            booking.cancel()
            messages.info(request, _(f"Заявка на бронирование «{booking.event_name}» отменена."))
        return redirect("requests:dashboard")


class PassRequestCreateView(LoginRequiredMixin, CreateView):
    """Подача заявки на пропуск с добавлением посетителей."""

    model = PassRequest
    form_class = PassRequestForm
    template_name = "requests/pass_request_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["visitor_formset"] = PassVisitorFormSet(self.request.POST, prefix="visitors")
        else:
            context["visitor_formset"] = PassVisitorFormSet(prefix="visitors")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        visitor_formset = context["visitor_formset"]

        if not visitor_formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, visitor_formset=visitor_formset)
            )

        with transaction.atomic():
            pass_req = form.save(commit=False)
            pass_req.user = self.request.user
            pass_req.status = PassRequest.Status.SUBMITTED
            pass_req.save()

            visitor_formset.instance = pass_req
            visitor_formset.save()

        messages.success(
            self.request,
            _(
                f"Заявка на пропуск «{pass_req.title}» "
                "успешно подана! Ожидайте согласования штабом."
            ),
        )
        return redirect(pass_req.get_absolute_url())


class PassRequestDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Просмотр статуса заявки на пропуск и списка гостей."""

    model = PassRequest
    template_name = "requests/pass_request_detail.html"
    context_object_name = "pass_request"

    def test_func(self):
        obj = self.get_object()
        return self.request.user.is_staff or obj.user == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["visitors"] = self.object.visitors.all()
        return context


class PassRequestCancelView(LoginRequiredMixin, View):
    """Отмена заявки на пропуск заявителем."""

    def post(self, request, pk):
        pass_req = get_object_or_404(PassRequest, pk=pk)
        if pass_req.user != request.user and not request.user.is_staff:
            raise PermissionDenied

        if pass_req.status in [PassRequest.Status.APPROVED, PassRequest.Status.SUBMITTED]:
            pass_req.cancel()
            messages.info(request, _(f"Заявка на пропуск «{pass_req.title}» отменена."))
        return redirect("requests:dashboard")
