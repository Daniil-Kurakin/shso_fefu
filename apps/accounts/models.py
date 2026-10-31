from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Системные роли. «Кандидат» — не роль, а состояние: пользователь без членства в отряде."""

    OWNER = "owner", _("Владелец")
    ADMIN = "admin", _("Админ")
    CURATOR = "curator", _("Куратор")
    SQUAD_STAFF = "squad_staff", _("Комсостав отряда")
    MEMBER = "member", _("Боец / участник")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.OWNER)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("consent_personal_data", True)
        extra_fields.setdefault("consent_date", timezone.now())
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email"), max_length=254, unique=True)
    full_name = models.CharField(_("ФИО"), max_length=200, blank=True)
    phone = models.CharField(_("номер телефона"), max_length=20, blank=True)
    role = models.CharField(_("системная роль"), max_length=20, choices=Role, default=Role.MEMBER)
    signature = models.CharField(
        _("подпись"),
        max_length=120,
        blank=True,
        help_text=_("Отображаемая подпись (например, «Комиссар по связям»). На права не влияет."),
    )
    avatar = models.ImageField(
        _("аватар / фото профиля"),
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    bio = models.TextField(
        _("о себе"),
        blank=True,
        help_text=_("Краткий рассказ о себе, увлечениях и опыте в студотрядах"),
    )
    vk_url = models.URLField(_("профиль ВКонтакте"), blank=True)
    telegram = models.CharField(
        _("Telegram"),
        max_length=100,
        blank=True,
        help_text=_("@username или ссылка"),
    )
    language = models.CharField(
        _("язык интерфейса"),
        max_length=2,
        choices=[("ru", "Русский"), ("en", "English")],
        default="ru",
    )
    # Статус учётной записи и подтверждение email (149-ФЗ)
    email_verified = models.BooleanField(_("email подтверждён"), default=False)
    is_active = models.BooleanField(_("активен"), default=True)
    is_staff = models.BooleanField(_("доступ в админ-панель"), default=False)
    date_joined = models.DateTimeField(_("дата регистрации"), default=timezone.now)

    # 152-ФЗ «О персональных данных» — согласие и аудит
    consent_personal_data = models.BooleanField(
        _("согласие на ОПД (152-ФЗ)"),
        default=True,
        help_text=_("Подтверждение факта дачи согласия на обработку персональных данных"),
    )
    consent_date = models.DateTimeField(
        _("дата и время согласия"),
        null=True,
        blank=True,
        help_text=_("Временная метка фиксации согласия"),
    )
    consent_ip = models.GenericIPAddressField(
        _("IP-адрес согласия"),
        null=True,
        blank=True,
        help_text=_("IP-адрес при даче согласия (для аудита 152-ФЗ)"),
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("пользователь")
        verbose_name_plural = _("пользователи")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        # Доступ в саму админ-панель Django (is_staff) разрешён только владельцу
        if not self.is_superuser and self.role != Role.OWNER:
            self.is_staff = False
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email

    def get_avatar_url(self) -> str | None:
        return self.avatar.url if self.avatar else None

    def get_initials(self) -> str:
        if self.full_name:
            parts = self.full_name.strip().split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return parts[0][0].upper()
        return self.email[0].upper()

    @property
    def is_hq_staff(self) -> bool:
        """Права штаба: владелец, администратор или куратор."""
        return bool(self.is_superuser or self.role in {Role.OWNER, Role.ADMIN, Role.CURATOR})

    @property
    def is_squad_command_staff(self) -> bool:
        """Права комсостава отряда или штаба."""
        if not self.is_authenticated:
            return False
        if self.is_hq_staff or self.role == Role.SQUAD_STAFF:
            return True
        from apps.squads.models import Membership

        return Membership.objects.filter(
            user=self,
            is_active=True,
            position__is_staff=True,
        ).exists()

    @property
    def is_owner(self) -> bool:
        """Права владельца сайта: доступ к Django админ-панели."""
        return bool(self.is_superuser or self.role == Role.OWNER)

    def get_managed_squads(self):
        """Возвращает queryset отрядов, которыми пользователь вправе управлять."""
        from apps.squads.models import Squad

        if not self.is_authenticated:
            return Squad.objects.none()
        if self.is_hq_staff:
            return Squad.objects.all().order_by("name")
        return (
            Squad.objects.filter(
                memberships__user=self,
                memberships__is_active=True,
                memberships__position__is_staff=True,
            )
            .distinct()
            .order_by("name")
        )

    def can_manage_squad(self, squad) -> bool:
        """Проверяет право пользователя управлять конкретным отрядом."""
        if not self.is_authenticated or not squad:
            return False
        if self.is_hq_staff:
            return True
        from apps.squads.models import Membership

        return Membership.objects.filter(
            user=self,
            squad=squad,
            is_active=True,
            position__is_staff=True,
        ).exists()


def get_current_year() -> int:
    return timezone.now().year


class UserPortfolioItem(models.Model):
    """Элемент личного портфолио бойца (целина, награда, мероприятие, проект)."""

    class Category(models.TextChoices):
        CELINA = "celina", _("Трудовой семестр / Целина")
        AWARD = "award", _("Награда / Знак отличия")
        EVENT = "event", _("Слёт / Мероприятие / Форум")
        PROJECT = "project", _("Проект / Волонтёрство")
        EDUCATION = "education", _("Обучение / Сертификат")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_items",
        verbose_name=_("пользователь"),
    )
    title = models.CharField(_("название"), max_length=200)
    category = models.CharField(
        _("категория"),
        max_length=30,
        choices=Category.choices,
        default=Category.CELINA,
    )
    year = models.PositiveSmallIntegerField(
        _("год"),
        default=get_current_year,
    )
    organization = models.CharField(
        _("организация / место"),
        max_length=200,
        blank=True,
        help_text=_("Например: ВДЦ «Океан», Приморский край или ШСО ДВФУ"),
    )
    description = models.TextField(
        _("описание"),
        blank=True,
        help_text=_("Краткое описание обязанностей, результатов, роли или впечатлений"),
    )
    image = models.ImageField(
        _("фотография / грамота"),
        upload_to="portfolio/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(_("дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("дата обновления"), auto_now=True)

    class Meta:
        verbose_name = _("элемент портфолио")
        verbose_name_plural = _("портфолио бойцов")
        ordering = ["-year", "-created_at"]

    def __str__(self):
        user_name = self.user.get_full_name() if self.user_id else "—"
        return f"{self.title} ({self.year}) — {user_name}"
