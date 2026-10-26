from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


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
