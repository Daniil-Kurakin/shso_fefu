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
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email"), max_length=254, unique=True)
    full_name = models.CharField(_("ФИО"), max_length=200, blank=True)
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
    is_active = models.BooleanField(_("активен"), default=True)
    is_staff = models.BooleanField(_("доступ в админ-панель"), default=False)
    date_joined = models.DateTimeField(_("дата регистрации"), default=timezone.now)

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
