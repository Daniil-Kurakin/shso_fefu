from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView

from apps.accounts.models import Role
from apps.squads.models import SquadPageRevision

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


class AdminModerationView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Панель администрирования и модерации для администраторов штаба:
    - Просмотр и согласование заявок на помещения кампуса (RoomBookingRequest);
    - Согласование гостевых пропусков (PassRequest);
    - Подтверждение публикации изменений отрядных страниц (SquadPageRevision).
    """

    template_name = "requests/moderation.html"

    def test_func(self):
        user = self.request.user
        return bool(
            user.is_authenticated and (user.is_hq_staff or user.role in {Role.OWNER, Role.ADMIN})
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self.request.GET.get("tab", "rooms")
        status_filter = self.request.GET.get("status", "all")

        # 1. Заявки на помещения
        room_qs = RoomBookingRequest.objects.select_related("room", "user", "squad").order_by(
            "-event_date", "-start_time"
        )
        if status_filter == "pending":
            room_qs = room_qs.filter(status=RoomBookingRequest.Status.SUBMITTED)
        elif status_filter == "approved":
            room_qs = room_qs.filter(status=RoomBookingRequest.Status.APPROVED)
        elif status_filter == "rejected":
            room_qs = room_qs.filter(status=RoomBookingRequest.Status.REJECTED)

        # 2. Заявки на пропуска
        pass_qs = (
            PassRequest.objects.select_related("user", "squad")
            .prefetch_related("visitors")
            .order_by("-visit_date", "-created_at")
        )
        if status_filter == "pending":
            pass_qs = pass_qs.filter(status=PassRequest.Status.SUBMITTED)
        elif status_filter == "approved":
            pass_qs = pass_qs.filter(status=PassRequest.Status.APPROVED)
        elif status_filter == "rejected":
            pass_qs = pass_qs.filter(status=PassRequest.Status.REJECTED)

        # 3. Ревизии страниц отрядов
        rev_qs = SquadPageRevision.objects.select_related(
            "squad", "author", "reviewed_by"
        ).order_by("-created_at")
        if status_filter == "pending":
            rev_qs = rev_qs.filter(status=SquadPageRevision.Status.PENDING)
        elif status_filter == "approved":
            rev_qs = rev_qs.filter(status=SquadPageRevision.Status.PUBLISHED)
        elif status_filter == "rejected":
            rev_qs = rev_qs.filter(status=SquadPageRevision.Status.RETURNED)

        context["tab"] = tab
        context["status_filter"] = status_filter
        context["room_bookings"] = room_qs
        context["pass_requests"] = pass_qs
        context["squad_revisions"] = rev_qs

        # Бейджи количества ожидающих согласования
        context["pending_rooms_count"] = RoomBookingRequest.objects.filter(
            status=RoomBookingRequest.Status.SUBMITTED
        ).count()
        context["pending_passes_count"] = PassRequest.objects.filter(
            status=PassRequest.Status.SUBMITTED
        ).count()
        context["pending_revisions_count"] = SquadPageRevision.objects.filter(
            status=SquadPageRevision.Status.PENDING
        ).count()
        context["total_pending_count"] = (
            context["pending_rooms_count"]
            + context["pending_passes_count"]
            + context["pending_revisions_count"]
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        target_id = request.POST.get("target_id")
        comment = request.POST.get("comment", "").strip()
        tab = request.POST.get("tab", "rooms")

        if action == "approve_room":
            obj = get_object_or_404(RoomBookingRequest, pk=target_id)
            obj.approve(request.user, comment=comment)
            messages.success(request, _(f"Бронь зала «{obj.room.name}» успешно одобрена."))

        elif action == "reject_room":
            obj = get_object_or_404(RoomBookingRequest, pk=target_id)
            obj.reject(request.user, comment=comment)
            messages.warning(request, _(f"Бронь зала «{obj.room.name}» отклонена."))

        elif action == "approve_pass":
            obj = get_object_or_404(PassRequest, pk=target_id)
            obj.approve(request.user, comment=comment)
            messages.success(request, _(f"Заявка на пропуск «{obj.title}» одобрена."))

        elif action == "reject_pass":
            obj = get_object_or_404(PassRequest, pk=target_id)
            obj.reject(request.user, comment=comment)
            messages.warning(request, _(f"Заявка на пропуск «{obj.title}» отклонена."))

        elif action == "publish_revision":
            obj = get_object_or_404(SquadPageRevision, pk=target_id)
            obj.publish(request.user)
            messages.success(
                request,
                _(f"Изменения страницы отряда «{obj.squad.name}» успешно опубликованы на сайте!"),
            )

        elif action == "reject_revision":
            obj = get_object_or_404(SquadPageRevision, pk=target_id)
            obj.reject(request.user, comment=comment)
            messages.warning(
                request, _(f"Ревизия изменений страницы отряда «{obj.squad.name}» отклонена.")
            )

        return redirect(f"{reverse('requests:moderation')}?tab={tab}")
