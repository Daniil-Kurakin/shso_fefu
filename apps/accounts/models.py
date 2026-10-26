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
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email

    @property
    def is_hq_staff(self) -> bool:
        """Права штаба: владелец, администратор или куратор."""
        return bool(self.is_superuser or self.role in {Role.OWNER, Role.ADMIN, Role.CURATOR})

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
