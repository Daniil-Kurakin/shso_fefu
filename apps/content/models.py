import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

VLADIVOSTOK_TZ = ZoneInfo("Asia/Vladivostok")


class Quote(models.Model):
    """Цитата бойца, ветерана или руководителя студотрядов."""

    text = models.TextField(_("текст цитаты"))
    author = models.CharField(_("автор"), max_length=150)
    author_title = models.CharField(
        _("должность / отряд автора"),
        max_length=200,
        blank=True,
        help_text=_("Например: «Комиссар СПО Лав», «Ветеран ШСО ДВФУ»"),
    )
    language = models.CharField(
        _("язык"),
        max_length=10,
        choices=[("ru", "Русский"), ("en", "English")],
        default="ru",
    )
    is_active = models.BooleanField(_("активна"), default=True)
    pinned_date = models.DateField(
        _("закреплена на дату"),
        null=True,
        blank=True,
        help_text=_("Если дата указана, цитата будет гарантированно показана в этот день"),
    )
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)

    class Meta:
        verbose_name = _("цитата")
        verbose_name_plural = _("цитаты")
        ordering = ["-pinned_date", "-created_at"]

    def __str__(self):
        return f"«{self.text[:50]}...» — {self.author}"

    @classmethod
    def get_quote_of_the_day(cls, for_date=None, lang="ru"):
        """
        Возвращает цитату дня:
        1. Сначала проверяется закрепление на дату (pinned_date).
        2. Если нет закрепления, детерминированно выбирается активная цитата по дню.
        3. Результат кэшируется до полуночи по Владивостоку.
        """
        now_vladivostok = timezone.now().astimezone(VLADIVOSTOK_TZ)
        today = for_date or now_vladivostok.date()

        cache_key = f"quote_of_the_day_{lang}_{today.isoformat()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Проверяем закреплённую цитату на этот день
        pinned = cls.objects.filter(is_active=True, pinned_date=today)
        quote = pinned.filter(language=lang).first() or pinned.filter(language="ru").first()

        # 2. Если закреплённой нет, выбираем детерминированно из банка активных цитат
        if not quote:
            quotes = list(cls.objects.filter(is_active=True, language=lang))
            if not quotes and lang != "ru":
                quotes = list(cls.objects.filter(is_active=True, language="ru"))

            if quotes:
                # Детерминированный выбор по дню: без повторов, пока не исчерпан банк
                # day_number позволяет плавно циклически перебирать весь список
                index = today.toordinal() % len(quotes)
                quote = quotes[index]

        # 3. Вычисляем количество секунд до полуночи во Владивостоке
        tomorrow = datetime.datetime.combine(
            today + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=VLADIVOSTOK_TZ,
        )
        seconds_to_midnight = max(int((tomorrow - now_vladivostok).total_seconds()), 60)

        cache.set(cache_key, quote, timeout=seconds_to_midnight)
        return quote


class StaffMember(models.Model):
    """Член руководящего состава штаба для страницы контактов."""

    full_name = models.CharField(_("ФИО"), max_length=200)
    position = models.CharField(_("должность"), max_length=150)
    position_en = models.CharField(_("должность (en)"), max_length=150, blank=True)
    responsibility = models.CharField(
        _("зона ответственности"),
        max_length=255,
        blank=True,
        help_text=_("Например: «Курирование сервисных и строительных отрядов»"),
    )
    email = models.EmailField(_("email"), blank=True)
    phone = models.CharField(_("телефон"), max_length=50, blank=True)
    vk_url = models.URLField(_("профиль VK"), blank=True)
    telegram_url = models.URLField(_("Telegram"), blank=True)
    photo = models.ImageField(
        _("фотография"),
        upload_to="content/staff/%Y/",
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField(_("порядок вывода"), default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
        verbose_name=_("привязанный аккаунт"),
    )
    is_active = models.BooleanField(_("активен"), default=True)

    class Meta:
        verbose_name = _("руководитель штаба")
        verbose_name_plural = _("руководство штаба")
        ordering = ["order", "full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.position})"


class SiteSetting(models.Model):
    """
    Настройки сайта, ключевые показатели и контактные данные штаба.
    Любая цифра сопровождается годом и источником (требование ТЗ).
    """

    key = models.CharField(_("ключ настройки"), max_length=60, unique=True)
    value = models.TextField(_("значение (ru)"))
    value_en = models.TextField(_("значение (en)"), blank=True)
    year = models.PositiveSmallIntegerField(
        _("актуальный год"),
        null=True,
        blank=True,
        help_text=_("Год, к которому относится цифра или факт"),
    )
    source = models.CharField(
        _("источник данных"),
        max_length=255,
        blank=True,
        help_text=_("Ссылка или автор подтверждения данных"),
    )
    description = models.CharField(_("описание для администратора"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("настройка сайта")
        verbose_name_plural = _("настройки сайта")
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}: {self.value}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Сбрасываем кэш при сохранении
        cache.delete(f"sitesetting_{self.key}_ru")
        cache.delete(f"sitesetting_{self.key}_en")
        cache.delete(f"sitesetting_obj_{self.key}")

    @classmethod
    def get(cls, key: str, default: str = "", lang: str = "ru") -> str:
        """Возвращает строковое значение настройки с кэшированием."""
        cache_key = f"sitesetting_{key}_{lang}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            setting = cls.objects.get(key=key)
            val = setting.value_en if lang == "en" and setting.value_en else setting.value
        except cls.DoesNotExist:
            val = default

        cache.set(cache_key, val, timeout=3600)
        return val

    @classmethod
    def get_setting_object(cls, key: str):
        """Возвращает полный объект настройки (включая год и источник)."""
        cache_key = f"sitesetting_obj_{key}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            obj = cls.objects.get(key=key)
        except cls.DoesNotExist:
            obj = None
        cache.set(cache_key, obj, timeout=3600)
        return obj
