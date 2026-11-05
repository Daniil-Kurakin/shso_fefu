from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Event(models.Model):
    """Событие в календаре ШСО ДВФУ."""

    class Category(models.TextChoices):
        GENERAL = "general", _("Общее мероприятие")
        HQ = "hq", _("Штабное собрание / слет")
        SCHOOL = "school", _("Обучение / Школа")
        SPORT = "sport", _("Спорт / Спартакиада")
        CULTURE = "culture", _("Творчество / Конкурс")
        VOLUNTEERING = "volunteering", _("Волонтерство / Акция")
        WORK = "work", _("Трудовой проект / Субботник")
        OTHER = "other", _("Другое")

    title = models.CharField(_("название события"), max_length=255)
    category = models.CharField(
        _("категория"),
        max_length=30,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    organizer = models.CharField(
        _("организатор"),
        max_length=255,
        default="ШСО ДВФУ",
        help_text=_("Организатор мероприятия (ШСО ДВФУ, ДМП, отряд и др.)"),
    )
    event_date = models.DateField(_("дата проведения"))
    start_time = models.TimeField(_("время начала"), blank=True, null=True)
    end_time = models.TimeField(_("время окончания"), blank=True, null=True)
    location = models.CharField(_("локация"), max_length=255)
    description = models.TextField(_("описание события"), blank=True)
    image = models.ImageField(
        _("афиша / обложка"),
        upload_to="events/%Y/%m/",
        blank=True,
        null=True,
    )
    url = models.URLField(
        _("ссылка на регистрацию / инфо"),
        blank=True,
        help_text=_("Ссылка на регистрацию, беседу или пост ВКонтакте"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_events",
        verbose_name=_("автор (администратор)"),
    )
    created_at = models.DateTimeField(_("создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("событие")
        verbose_name_plural = _("события календаря")
        ordering = ["event_date", "start_time", "title"]

    def __str__(self):
        return f"{self.title} ({self.event_date})"

    def get_absolute_url(self):
        return reverse("events:detail", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValidationError(
                {"end_time": _("Время окончания не может быть раньше времени начала.")}
            )
