from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Direction, Membership, Position, Squad, SquadPageRevision, SquadTransferRequest


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ("user", "position", "start_date", "end_date", "is_active", "is_veteran")
    raw_id_fields = ("user",)


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order", "squads_count")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")

    @admin.display(description=_("Отрядов"))
    def squads_count(self, obj):
        return obj.squads.count()


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_staff", "can_initiate_transfer", "order")
    list_editable = ("is_staff", "can_initiate_transfer", "order")
    search_fields = ("name",)
    ordering = ("order", "name")


@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "direction",
        "founding_year",
        "is_recruiting",
        "active_members_count_display",
        "created_at",
    )
    list_filter = ("direction", "is_recruiting", "founding_year")
    search_fields = ("name", "motto", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]
    ordering = ("name",)

    @admin.display(description=_("Бойцов"))
    def active_members_count_display(self, obj):
        return obj.active_members_count


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "squad",
        "position",
        "start_date",
        "end_date",
        "is_active",
        "is_veteran",
    )
    list_filter = ("is_active", "is_veteran", "squad", "position")
    search_fields = ("user__email", "user__full_name", "squad__name")
    raw_id_fields = ("user",)
    ordering = ("-is_active", "-start_date")
    actions = ["action_convert_to_veteran", "action_restore_to_active"]

    @admin.action(description=_("Перевести выбранных бойцов в ветераны"))
    def action_convert_to_veteran(self, request, queryset):
        for m in queryset:
            m.convert_to_veteran()
        self.message_user(request, _(f"Переведено в ветераны: {queryset.count()}"))

    @admin.action(description=_("Вернуть выбранных в активный состав"))
    def action_restore_to_active(self, request, queryset):
        restored = 0
        for m in queryset:
            try:
                m.restore_to_active()
                restored += 1
            except Exception as e:
                self.message_user(request, f"Ошибка при возврате {m.user}: {e}", level="error")
        self.message_user(request, _(f"Возвращено в активный состав: {restored}"))


@admin.register(SquadPageRevision)
class SquadPageRevisionAdmin(admin.ModelAdmin):
    list_display = (
        "squad",
        "author",
        "status",
        "is_recruiting",
        "created_at",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("status", "squad", "is_recruiting")
    search_fields = ("squad__name", "motto", "description", "author__email")
    actions = ["action_publish", "action_return_for_revision"]

    @admin.action(description=_("Одобрить и опубликовать выбранные ревизии"))
    def action_publish(self, request, queryset):
        for revision in queryset:
            revision.publish(moderator=request.user)
        self.message_user(request, _("Выбранные ревизии опубликованы."))

    @admin.action(description=_("Вернуть на доработку"))
    def action_return_for_revision(self, request, queryset):
        count = queryset.update(status=SquadPageRevision.Status.RETURNED)
        self.message_user(request, _(f"Возвращено на доработку: {count}"))


@admin.register(SquadTransferRequest)
class SquadTransferRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "from_squad",
        "to_squad",
        "new_position",
        "initiator",
        "status",
        "created_at",
        "decided_by",
    )
    list_filter = ("status", "from_squad", "to_squad")
    search_fields = ("user__email", "user__full_name", "from_squad__name", "to_squad__name")
    actions = ["action_approve", "action_reject"]

    @admin.action(description=_("Одобрить выбранные переходы"))
    def action_approve(self, request, queryset):
        for transfer in queryset.filter(status=SquadTransferRequest.Status.PENDING):
            transfer.approve(admin_user=request.user)
        self.message_user(request, _("Выбранные переходы подтверждены, членства обновлены."))

    @admin.action(description=_("Отклонить выбранные переходы"))
    def action_reject(self, request, queryset):
        for transfer in queryset.filter(status=SquadTransferRequest.Status.PENDING):
            transfer.reject(admin_user=request.user)
        self.message_user(request, _("Выбранные переходы отклонены."))
