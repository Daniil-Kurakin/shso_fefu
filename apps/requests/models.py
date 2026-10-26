import contextlib
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CampusPremise(models.Model):
    """
    Помещение или зал кампуса ДВФУ, доступное для бронирования отрядами.
    (А826, А3 «Синий зал», коворкинг «Аякс», аудитории C5, E3 и др.).
    """

    class Building(models.TextChoices):
        CORPUS_A = "A", _("Корпус A (Главный)")
        CORPUS_B = "B", _("Корпус B")
        CORPUS_C = "C", _("Корпус C")
        CORPUS_D = "D", _("Корпус D")
        CORPUS_E = "E", _("Корпус E")
        CORPUS_F = "F", _("Корпус F")
        CORPUS_G = "G", _("Корпус G")
        CORPUS_M = "M", _("Корпус M (Медицинский)")
        OTHER = "other", _("Другой объект кампуса")

    name = models.CharField(_("название помещения / зала"), max_length=150)
    building = models.CharField(
        _("корпус"),
        max_length=10,
        choices=Building.choices,
        default=Building.CORPUS_A,
    )
    floor = models.PositiveSmallIntegerField(_("этаж"), null=True, blank=True)
    room_number = models.CharField(_("номер аудитории / кабинета"), max_length=20, blank=True)
    capacity = models.PositiveIntegerField(
        _("вместимость (чел.)"),
        default=30,
        help_text=_("Максимальное количество посадочных мест"),
    )
    equipment_description = models.TextField(
        _("доступное оборудование"),
        blank=True,
        help_text=_("Проектор, экран, колонки, микрофоны, флипчарт, кликер и т.д."),
    )
    is_active = models.BooleanField(
        _("доступно для бронирования"),
        default=True,
        help_text=_("Если выключено, помещение скрыто из формы подачи заявок"),
    )
    order = models.PositiveIntegerField(_("порядок в списке"), default=100)

    class Meta:
        verbose_name = _("помещение кампуса")
        verbose_name_plural = _("помещения кампуса")
        ordering = ["building", "order", "name"]

    def __str__(self):
        code = f" [{self.room_number}]" if self.room_number else ""
        return f"{self.name}{code} ({self.get_building_display()})"


class RoomBookingRequest(models.Model):
    """Заявка на бронирование аудитории или зала кампуса ДВФУ."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        SUBMITTED = "submitted", _("На рассмотрении")
        APPROVED = "approved", _("Одобрено")
        REJECTED = "rejected", _("Отклонено")
        CANCELLED = "cancelled", _("Отменено заявителем")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="room_bookings",
        verbose_name=_("заявитель"),
    )
    squad = models.ForeignKey(
        "squads.Squad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_bookings",
        verbose_name=_("отряд"),
        help_text=_("Укажите отряд, если бронь производится от имени отряда"),
    )
    room = models.ForeignKey(
        CampusPremise,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("помещение"),
    )
    event_name = models.CharField(_("название мероприятия / встречи"), max_length=200)
    event_date = models.DateField(_("дата бронирования"))
    start_time = models.TimeField(_("время начала"))
    end_time = models.TimeField(_("время окончания"))
    expected_participants = models.PositiveIntegerField(
        _("ожидаемое число участников"),
        default=10,
    )
    equipment_required = models.TextField(
        _("требуемое оборудование"),
        blank=True,
        help_text=_("Укажите, что необходимо предоставить (проектор, микрофон и др.)"),
    )
    status = models.CharField(
        _("статус заявки"),
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    moderator_comment = models.TextField(
        _("комментарий штаба"),
        blank=True,
        help_text=_("Причина отклонения, инструкции по получению ключей или ответ заявителю"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_room_bookings",
        verbose_name=_("кто рассмотрел"),
    )
    reviewed_at = models.DateTimeField(_("дата рассмотрения"), null=True, blank=True)
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    class Meta:
        verbose_name = _("заявка на помещение")
        verbose_name_plural = _("заявки на помещения")
        ordering = ["-event_date", "-start_time"]

    def __str__(self):
        user_display = self.user.get_full_name() if self.user_id else "—"
        room_display = self.room.name if self.room_id else "—"
        date_str = self.event_date.strftime("%d.%m.%Y") if self.event_date else "—"
        return f"{self.event_name} — {room_display} ({date_str}) [{user_display}]"

    def get_absolute_url(self):
        return reverse("requests:room_detail", kwargs={"pk": self.pk})

    def get_conflicting_bookings(self):
        """
        Поиск пересечений по времени в том же помещении на ту же дату.
        Возвращает заявки в статусе Одобрено или На рассмотрении.
        """
        if not self.room_id or not self.event_date or not self.start_time or not self.end_time:
            return RoomBookingRequest.objects.none()

        qs = RoomBookingRequest.objects.filter(
            room_id=self.room_id,
            event_date=self.event_date,
            status__in=[self.Status.SUBMITTED, self.Status.APPROVED],
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs

    def has_approved_collision(self) -> bool:
        """Есть ли уже одобренная бронь на этот временной интервал."""
        return self.get_conflicting_bookings().filter(status=self.Status.APPROVED).exists()

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(
                {"end_time": _("Время окончания должно быть строго позже времени начала.")}
            )

        if not self.pk and self.event_date and self.event_date < timezone.localdate():
            raise ValidationError(
                {"event_date": _("Нельзя забронировать помещение на прошедшую дату.")}
            )

        # Если статус меняется на Одобрено, проверяем отсутствие коллизий с другими одобренными
        if self.status == self.Status.APPROVED and self.has_approved_collision():
            conflict = self.get_conflicting_bookings().filter(status=self.Status.APPROVED).first()
            c_time = (
                f"{conflict.start_time.strftime('%H:%M')} - {conflict.end_time.strftime('%H:%M')}"
            )
            raise ValidationError(
                _(
                    f"Коллизия: помещение уже одобрено для заявки «{conflict.event_name}» "
                    f"на {c_time}. Невозможно одобрить две пересекающиеся заявки."
                )
            )

    def approve(self, moderator, comment=""):
        self.status = self.Status.APPROVED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        if comment:
            self.moderator_comment = comment
        self.clean()
        self.save()

    def reject(self, moderator, comment=""):
        self.status = self.Status.REJECTED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        if comment:
            self.moderator_comment = comment
        self.save()

    def cancel(self):
        """Отмена заявки заявителем."""
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])


class PassRequest(models.Model):
    """
    Заявка на оформление разового или временного пропуска на территорию кампуса ДВФУ.
    Соответствует требованиям 152-ФЗ с автоматической очисткой ПДн через 30 дней.
    """

    class PassType(models.TextChoices):
        INDIVIDUAL = "individual", _("Индивидуальный пропуск")
        GROUP = "group", _("Групповой пропуск (от 2 чел.)")
        VEHICLE = "vehicle", _("Транспортный пропуск (с въездом авто)")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        SUBMITTED = "submitted", _("На рассмотрении")
        APPROVED = "approved", _("Одобрено")
        REJECTED = "rejected", _("Отклонено")
        CANCELLED = "cancelled", _("Отменено заявителем")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pass_requests",
        verbose_name=_("заявитель"),
    )
    squad = models.ForeignKey(
        "squads.Squad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pass_requests",
        verbose_name=_("отряд"),
    )
    title = models.CharField(
        _("цель визита / мероприятие"),
        max_length=200,
        help_text=_("Например: «Спикер на школу комсостава» или «Монтаж выставки»"),
    )
    pass_type = models.CharField(
        _("тип пропуска"),
        max_length=20,
        choices=PassType.choices,
        default=PassType.INDIVIDUAL,
    )
    visit_date = models.DateField(_("дата визита (с)"))
    visit_end_date = models.DateField(
        _("дата окончания визита (по)"),
        null=True,
        blank=True,
        help_text=_("Заполняется для многодневных мероприятий"),
    )
    entry_point = models.CharField(
        _("КПП въезда / прохода"),
        max_length=150,
        default="Центральный КПП (корпус А)",
        help_text=_("Например: Северные ворота, Южные ворота, КПП корпуса А, КПП Г"),
    )
    car_model = models.CharField(
        _("марка автомобиля"),
        max_length=80,
        blank=True,
        help_text=_("Обязательно для транспортных пропусков"),
    )
    car_number = models.CharField(
        _("госномер автомобиля"),
        max_length=30,
        blank=True,
        help_text=_("Например: А123ВС 125"),
    )
    official_note = models.FileField(
        _("служебная записка / обоснование"),
        upload_to="pass_notes/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Скан служебной записки с подписью руководства (при наличии)"),
    )
    status = models.CharField(
        _("статус заявки"),
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    moderator_comment = models.TextField(
        _("комментарий штаба"),
        blank=True,
        help_text=_("Номер служебной записки в СЭД, резолюция СБ или причина отказа"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_pass_requests",
        verbose_name=_("кто рассмотрел"),
    )
    reviewed_at = models.DateTimeField(_("дата рассмотрения"), null=True, blank=True)
    data_deletion_scheduled_at = models.DateField(
        _("плановая дата очистки ПДн (152-ФЗ)"),
        null=True,
        blank=True,
        help_text=_("По закону ПДн гостей удаляются через 30 дней после мероприятия"),
    )
    is_data_purged = models.BooleanField(
        _("персональные данные удалены"),
        default=False,
        help_text=_("Флаг автоматической очистки конфиденциальных данных гостей"),
    )
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    class Meta:
        verbose_name = _("заявка на пропуск")
        verbose_name_plural = _("заявки на пропуска")
        ordering = ["-visit_date", "-created_at"]

    def __str__(self):
        user_display = self.user.get_full_name() if self.user_id else "—"
        date_str = self.visit_date.strftime("%d.%m.%Y") if self.visit_date else "—"
        return f"Пропуск: {self.title} ({date_str}) [{user_display}]"

    def save(self, *args, **kwargs):
        # Автоматический расчет срока очистки ПДн: 30 дней после даты окончания визита
        if self.visit_date and not self.data_deletion_scheduled_at:
            target_date = self.visit_end_date or self.visit_date
            self.data_deletion_scheduled_at = target_date + timedelta(days=30)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("requests:pass_detail", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        if self.visit_end_date and self.visit_date and self.visit_end_date < self.visit_date:
            raise ValidationError(
                {"visit_end_date": _("Дата окончания визита не может быть раньше даты начала.")}
            )
        if self.pass_type == self.PassType.VEHICLE and not self.car_number:
            raise ValidationError(
                {"car_number": _("Для транспортного пропуска необходимо указать госномер авто.")}
            )

    def purge_personal_data(self):
        """Очистка персональных данных в соответствии с 152-ФЗ."""
        for visitor in self.visitors.all():
            visitor.document_data = "*** ПДн очищены по истечении 30 дней (152-ФЗ) ***"
            visitor.phone = ""
            visitor.save(update_fields=["document_data", "phone"])

        if self.official_note:
            with contextlib.suppress(Exception):
                self.official_note.delete(save=False)
            self.official_note = None

        self.is_data_purged = True
        self.save(update_fields=["official_note", "is_data_purged", "updated_at"])

    def approve(self, moderator, comment=""):
        self.status = self.Status.APPROVED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        if comment:
            self.moderator_comment = comment
        self.save()

    def reject(self, moderator, comment=""):
        self.status = self.Status.REJECTED
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        if comment:
            self.moderator_comment = comment
        self.save()

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])


class PassVisitor(models.Model):
    """
    Посетитель / гость в заявке на пропуск.
    Изолированное хранение ПДн с возможностью очистки.
    """

    class DocumentType(models.TextChoices):
        PASSPORT = "passport", _("Паспорт гражданина РФ")
        STUDENT_ID = "student_id", _("Студенческий билет стороннего вуза")
        BIRTH_CERT = "birth_certificate", _("Свидетельство о рождении")
        FOREIGN_PASSPORT = "foreign_passport", _("Заграничный паспорт")
        OTHER = "other", _("Иной документ")

    request = models.ForeignKey(
        PassRequest,
        on_delete=models.CASCADE,
        related_name="visitors",
        verbose_name=_("заявка на пропуск"),
    )
    full_name = models.CharField(_("ФИО посетителя"), max_length=200)
    document_type = models.CharField(
        _("тип документа"),
        max_length=25,
        choices=DocumentType.choices,
        default=DocumentType.PASSPORT,
    )
    document_data = models.CharField(
        _("серия, номер документа"),
        max_length=150,
        help_text=_("Серия и номер документа, удостоверяющего личность"),
    )
    organization = models.CharField(
        _("организация / город / вуз"),
        max_length=150,
        blank=True,
    )
    phone = models.CharField(_("контактный телефон"), max_length=50, blank=True)
    created_at = models.DateTimeField(_("добавлен"), auto_now_add=True)

    class Meta:
        verbose_name = _("посетитель")
        verbose_name_plural = _("список посетителей")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.get_document_type_display()})"
