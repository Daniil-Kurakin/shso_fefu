from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role


class Direction(models.Model):
    """Направление деятельности отрядов (педагогические, строительные и т.д.)."""

    name = models.CharField(_("название"), max_length=100, unique=True)
    slug = models.SlugField(_("URL"), max_length=100, unique=True, allow_unicode=True)
    icon = models.CharField(
        _("иконка / эмодзи"),
        max_length=50,
        blank=True,
        default="🏕️",
        help_text=_("Эмодзи или класс иконки для отображения в каталоге"),
    )
    description = models.TextField(_("описание"), blank=True)
    order = models.PositiveIntegerField(_("порядок сортировки"), default=0)

    class Meta:
        verbose_name = _("направление")
        verbose_name_plural = _("направления")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Position(models.Model):
    """Справочник должностей в отряде (командир, комиссар, боец и т.д.)."""

    name = models.CharField(_("название"), max_length=100, unique=True)
    name_en = models.CharField(_("название (en)"), max_length=100, blank=True)
    is_staff = models.BooleanField(
        _("комсостав"),
        default=False,
        help_text=_("Относится ли к руководящему составу отряда (дает роль «Комсостав» в системе)"),
    )
    can_initiate_transfer = models.BooleanField(
        _("право инициировать переход"),
        default=False,
        help_text=_("Право подавать заявки на переход бойцов (привязано к должности командира)"),
    )
    order = models.PositiveIntegerField(_("порядок вывода"), default=0)

    class Meta:
        verbose_name = _("должность")
        verbose_name_plural = _("справочник должностей")
        ordering = ["order", "name"]

    def __str__(self):
        staff_mark = f" ({_('комсостав')})" if self.is_staff else ""
        return f"{self.name}{staff_mark}"


class Squad(models.Model):
    """Студенческий отряд."""

    name = models.CharField(_("название отряда"), max_length=150, unique=True)
    slug = models.SlugField(_("URL"), max_length=150, unique=True, allow_unicode=True)
    direction = models.ForeignKey(
        Direction,
        on_delete=models.PROTECT,
        related_name="squads",
        verbose_name=_("направление"),
    )
    logo = models.ImageField(
        _("логотип"),
        upload_to="squads/logos/",
        blank=True,
        null=True,
    )
    motto = models.CharField(_("девиз"), max_length=255, blank=True)
    description = models.TextField(_("описание отряда"), blank=True)
    achievements = models.TextField(
        _("достижения (с указанием года)"),
        blank=True,
        help_text=_("Список побед и наград отряда по годам"),
    )
    founding_year = models.PositiveSmallIntegerField(
        _("год основания"),
        blank=True,
        null=True,
    )
    is_recruiting = models.BooleanField(
        _("набор открыт"),
        default=False,
        help_text=_("Идет ли сейчас набор в данный отряд"),
    )
    contact_url = models.URLField(
        _("ссылка на связь / сообщество"),
        blank=True,
        help_text=_("Ссылка на группу VK или Telegram-канал отряда"),
    )
    created_at = models.DateTimeField(_("дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("дата обновления"), auto_now=True)

    class Meta:
        verbose_name = _("отряд")
        verbose_name_plural = _("отряды")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("squads:detail", kwargs={"slug": self.slug})

    @property
    def active_members_count(self):
        return self.memberships.filter(is_active=True).count()

    def get_commander(self):
        membership = (
            self.memberships.filter(
                is_active=True,
                position__can_initiate_transfer=True,
            )
            .select_related("user", "position")
            .first()
        )
        return membership.user if membership else None


class Membership(models.Model):
    """
    Членство пользователя в отряде с сохранением полной истории.
    Один человек одновременно может активно состоять только в одном отряде.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("пользователь"),
    )
    squad = models.ForeignKey(
        Squad,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("отряд"),
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="memberships",
        verbose_name=_("должность"),
    )
    start_date = models.DateField(_("дата вступления"), default=timezone.now)
    end_date = models.DateField(_("дата выхода"), null=True, blank=True)
    is_active = models.BooleanField(_("активное членство"), default=True)
    created_at = models.DateTimeField(_("создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("членство в отряде")
        verbose_name_plural = _("членства в отрядах")
        ordering = ["-is_active", "-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="unique_active_membership_per_user",
            )
        ]

    def __str__(self):
        status = _("активен") if self.is_active else _("в архиве")
        user_name = self.user.get_full_name() if self.user_id else "—"
        squad_name = self.squad.name if self.squad_id else "—"
        pos_name = self.position.name if self.position_id else "—"
        return f"{user_name} — {squad_name} ({pos_name}, {status})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Автоматическая синхронизация системной роли пользователя
        if (
            self.user_id
            and self.position_id
            and self.is_active
            and self.user.role not in {Role.OWNER, Role.ADMIN}
        ):
            if self.position.is_staff:
                self.user.role = Role.SQUAD_STAFF
            else:
                self.user.role = Role.MEMBER
            self.user.save(update_fields=["role"])

    def clean(self):
        super().clean()
        if not self.user_id:
            return
        if self.is_active:
            existing = (
                Membership.objects.filter(user_id=self.user_id, is_active=True)
                .exclude(pk=self.pk)
                .first()
            )
            if existing:
                raise ValidationError(
                    _(
                        f"Пользователь уже активно состоит в отряде «{existing.squad.name}». "
                        "Один человек может состоять только в одном отряде одновременно."
                    )
                )


class SquadPageRevision(models.Model):
    """
    Ревизия страницы отряда.
    Комсостав заполняет черновик и отправляет на согласование.
    До момента одобрения на сайте отображается текущая активная версия отряда.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        PENDING = "pending", _("На согласовании")
        PUBLISHED = "published", _("Опубликована")
        RETURNED = "returned", _("Возвращена с комментарием")

    squad = models.ForeignKey(
        Squad,
        on_delete=models.CASCADE,
        related_name="revisions",
        verbose_name=_("отряд"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="squad_revisions",
        verbose_name=_("автор ревизии"),
    )
    motto = models.CharField(_("девиз"), max_length=255, blank=True)
    description = models.TextField(_("описание отряда"), blank=True)
    achievements = models.TextField(_("достижения (с указанием года)"), blank=True)
    contact_url = models.URLField(_("ссылка на связь / сообщество"), blank=True)
    is_recruiting = models.BooleanField(_("набор открыт"), default=False)

    status = models.CharField(
        _("статус согласования"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    moderator_comment = models.TextField(
        _("комментарий модератора"),
        blank=True,
        help_text=_("Пояснение, что исправить при возврате"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_squad_revisions",
        verbose_name=_("проверил"),
    )
    reviewed_at = models.DateTimeField(_("дата проверки"), null=True, blank=True)
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    class Meta:
        verbose_name = _("ревизия страницы отряда")
        verbose_name_plural = _("ревизии страниц отрядов")
        ordering = ["-created_at"]

    def __str__(self):
        squad_name = self.squad.name if self.squad_id else "—"
        return f"{squad_name} (ревизия #{self.pk or 'новая'} — {self.get_status_display()})"

    @transaction.atomic
    def publish(self, moderator):
        """Публикация ревизии с обновлением общедоступных данных отряда."""
        self.status = self.Status.PUBLISHED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        self.save()

        # Применяем данные к опубликованному отряду
        self.squad.motto = self.motto
        self.squad.description = self.description
        self.squad.achievements = self.achievements
        self.squad.contact_url = self.contact_url
        self.squad.is_recruiting = self.is_recruiting
        self.squad.save()

    def reject(self, moderator, comment=""):
        """Отклонение / возврат ревизии страницы отряда с комментарием."""
        self.status = self.Status.RETURNED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        if comment:
            self.moderator_comment = comment
        self.save()


class SquadTransferRequest(models.Model):
    """
    Заявка на переход бойца между отрядами.
    Создает командир исходного отряда с прикреплением закрытых подтверждающих документов.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("На рассмотрении")
        APPROVED = "approved", _("Одобрен")
        REJECTED = "rejected", _("Отклонен")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transfer_requests",
        verbose_name=_("боец"),
    )
    from_squad = models.ForeignKey(
        Squad,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        verbose_name=_("исходный отряд"),
    )
    to_squad = models.ForeignKey(
        Squad,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        verbose_name=_("целевой отряд"),
    )
    new_position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        verbose_name=_("должность в новом отряде"),
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_transfers",
        verbose_name=_("инициатор (командир)"),
    )
    document = models.FileField(
        _("документ / заявление (PDF или скан)"),
        upload_to="transfers/%Y/%m/",
        help_text=_("Заявление бойца и согласие командиров"),
    )
    status = models.CharField(
        _("статус заявки"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    decision_comment = models.TextField(_("комментарий к решению"), blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_transfers",
        verbose_name=_("кто рассмотрел"),
    )
    decided_at = models.DateTimeField(_("дата решения"), null=True, blank=True)
    created_at = models.DateTimeField(_("дата подачи"), auto_now_add=True)

    class Meta:
        verbose_name = _("заявка на переход")
        verbose_name_plural = _("заявки на переходы")
        ordering = ["-created_at"]

    def __str__(self):
        user_name = self.user.get_full_name() if self.user_id else "—"
        from_name = self.from_squad.name if self.from_squad_id else "—"
        to_name = self.to_squad.name if self.to_squad_id else "—"
        return f"Переход: {user_name} из «{from_name}» в «{to_name}»"

    @transaction.atomic
    def approve(self, admin_user, comment=""):
        """
        Атомарное подтверждение перехода:
        1. Закрывается старое членство (end_date = now, is_active = False).
        2. Открывается новое членство в один шаг.
        3. Заявка помечается одобренной.
        """
        today = timezone.now().date()

        # 1. Закрываем старое членство
        Membership.objects.filter(
            user=self.user,
            squad=self.from_squad,
            is_active=True,
        ).update(is_active=False, end_date=today)

        # 2. Создаем новое членство
        Membership.objects.create(
            user=self.user,
            squad=self.to_squad,
            position=self.new_position,
            start_date=today,
            is_active=True,
        )

        # 3. Обновляем статус заявки
        self.status = self.Status.APPROVED
        self.decided_by = admin_user
        self.decision_comment = comment
        self.decided_at = timezone.now()
        self.save()

    def reject(self, admin_user, comment=""):
        """Отклонение перехода с комментарием."""
        self.status = self.Status.REJECTED
        self.decided_by = admin_user
        self.decision_comment = comment
        self.decided_at = timezone.now()
        self.save()
