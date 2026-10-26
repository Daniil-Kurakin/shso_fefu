from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class VacancyQuerySet(models.QuerySet):
    def open(self):
        """Открытые вакансии с неистекшим сроком приёма."""
        today = timezone.now().date()
        return self.filter(
            status=Vacancy.Status.OPEN,
        ).filter(models.Q(deadline__isnull=True) | models.Q(deadline__gte=today))


class Vacancy(models.Model):
    """
    Вакансия или набор.
    Два типа: общая заявка на вступление в ШСО и рабочие места на кампусе (проекты типа «Аякс»).
    """

    class Type(models.TextChoices):
        JOIN_SQUAD = "join_squad", _("Вступление в студотряд")
        CAMPUS_JOB = "campus_job", _("Работа на кампусе")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        OPEN = "open", _("Открыта")
        CLOSED = "closed", _("Закрыта")
        ARCHIVED = "archived", _("В архиве")

    title = models.CharField(_("название"), max_length=200)
    slug = models.SlugField(_("URL"), max_length=200, unique=True, allow_unicode=True)
    type = models.CharField(
        _("тип вакансии"),
        max_length=20,
        choices=Type.choices,
        default=Type.JOIN_SQUAD,
    )
    description = models.TextField(_("описание вакансии / набора"))
    requirements = models.TextField(_("требования к кандидату"), blank=True)
    salary = models.CharField(
        _("оплата / ставка"),
        max_length=100,
        blank=True,
        help_text=_("Например: «Почасовая от 350 ₽/час» или «По итогам собеседования»"),
    )
    schedule = models.CharField(
        _("график и даты работы"),
        max_length=150,
        blank=True,
        help_text=_("Например: «Смены 2/2, лето 2026» или «Гибкий график»"),
    )
    slots_count = models.PositiveSmallIntegerField(
        _("число мест"),
        null=True,
        blank=True,
        help_text=_("Оставьте пустым, если число мест не ограничено"),
    )
    squad = models.ForeignKey(
        "squads.Squad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vacancies",
        verbose_name=_("отряд / проект"),
        help_text=_("Укажите отряд, если вакансия открыта конкретным отрядом"),
    )
    deadline = models.DateField(
        _("срок приёма заявок"),
        null=True,
        blank=True,
        help_text=_("Дата, после которой приём откликов автоматически прекращается"),
    )
    status = models.CharField(
        _("статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    objects = VacancyQuerySet.as_manager()

    class Meta:
        verbose_name = _("вакансия")
        verbose_name_plural = _("вакансии и наборы")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("vacancies:detail", kwargs={"slug": self.slug})

    @property
    def is_accepting_applications(self) -> bool:
        """Принимает ли вакансия отклики прямо сейчас."""
        if self.status != self.Status.OPEN:
            return False
        return not (self.deadline and self.deadline < timezone.now().date())

    @property
    def applications_count(self) -> int:
        return self.applications.count()


class VacancyApplication(models.Model):
    """
    Отклик кандидата на вакансию или общую заявку на вступление.
    Доступен как гостям, так и вошедшим пользователям.
    """

    class ContactType(models.TextChoices):
        TELEGRAM = "telegram", _("Telegram")
        VK = "vk", _("ВКонтакте")
        PHONE = "phone", _("Телефон")
        EMAIL = "email", _("Email")
        OTHER = "other", _("Другой контакт")

    class Status(models.TextChoices):
        NEW = "new", _("Новый")
        VIEWED = "viewed", _("Просмотрен")
        CONTACTED = "contacted", _("Связались")
        INVITED = "invited", _("Приглашён на собеседование")
        ACCEPTED = "accepted", _("Принят")
        REJECTED = "rejected", _("Отказ")

    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.CASCADE,
        related_name="applications",
        verbose_name=_("вакансия"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vacancy_applications",
        verbose_name=_("аккаунт пользователя"),
        help_text=_("Заполняется автоматически, если отклик подан авторизованным пользователем"),
    )
    applicant_name = models.CharField(_("как к вам обращаться"), max_length=150)
    contact_type = models.CharField(
        _("тип контакта"),
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.TELEGRAM,
    )
    contact_value = models.CharField(_("значение контакта"), max_length=150)
    data_consent = models.BooleanField(
        _("согласие на обработку персональных данных"),
        default=True,
    )
    status = models.CharField(
        _("статус рассмотрения"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    internal_comment = models.TextField(
        _("внутренний комментарий штаба"),
        blank=True,
        help_text=_("Заметки модератора по кандидату (не видны соискателю)"),
    )
    assigned_squad = models.ForeignKey(
        "squads.Squad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_applications",
        verbose_name=_("назначенный отряд"),
        help_text=_("Отряд, в который определен кандидат"),
    )
    created_at = models.DateTimeField(_("дата подачи"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлен"), auto_now=True)

    class Meta:
        verbose_name = _("отклик")
        verbose_name_plural = _("отклики на вакансии")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("contact_value"),
                "vacancy",
                "contact_type",
                name="unique_app_contact_per_vacancy",
            )
        ]

    def __str__(self):
        contact = f"{self.get_contact_type_display()}: {self.contact_value}"
        return f"{self.applicant_name} ({contact}) — {self.vacancy.title}"

    def save(self, *args, **kwargs):
        self.contact_value = self.contact_value.strip()
        super().save(*args, **kwargs)
