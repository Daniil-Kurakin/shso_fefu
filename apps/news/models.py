from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class NewsQuerySet(models.QuerySet):
    def published(self):
        """Только опубликованные новости с наступившей датой публикации."""
        return self.filter(
            status=News.Status.PUBLISHED,
            published_at__lte=timezone.now(),
        )


class News(models.Model):
    """Событие или новость штаба / отряда."""

    class Category(models.TextChoices):
        EVENTS = "events", _("Мероприятия")
        WORK_SEMESTER = "work_semester", _("Трудовой семестр")
        ACHIEVEMENTS = "achievements", _("Достижения")
        ANNOUNCEMENTS = "announcements", _("Объявления")

    class Organizer(models.TextChoices):
        SHSO = "shso", _("ШСО ДВФУ")
        FEFU = "fefu", _("ДВФУ")
        RSO = "rso", _("РСО")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        PENDING = "pending", _("На согласовании")
        PUBLISHED = "published", _("Опубликована")
        RETURNED = "returned", _("Возвращена с комментарием")

    title = models.CharField(_("заголовок"), max_length=255)
    slug = models.SlugField(_("URL"), max_length=255, unique=True, allow_unicode=True)
    lead = models.TextField(
        _("краткий анонс"),
        blank=True,
        help_text=_("Краткое содержание для карточки в ленте событий"),
    )
    content = models.TextField(_("текст новости"))
    category = models.CharField(
        _("категория"),
        max_length=30,
        choices=Category.choices,
        default=Category.EVENTS,
    )
    organizer = models.CharField(
        _("организатор"),
        max_length=30,
        choices=Organizer.choices,
        default=Organizer.SHSO,
    )
    squad = models.ForeignKey(
        "squads.Squad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news",
        verbose_name=_("отряд"),
        help_text=_("Укажите отряд, если новость относится к конкретному отряду"),
    )
    cover = models.ImageField(
        _("главное изображение (обложка)"),
        upload_to="news/covers/%Y/%m/",
        blank=True,
        null=True,
    )
    status = models.CharField(
        _("статус публикации"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="news_created",
        verbose_name=_("автор"),
    )
    moderator_comment = models.TextField(
        _("комментарий модератора"),
        blank=True,
        help_text=_("Заполняется при возврате на доработку с пояснением, что исправить"),
    )
    source_url = models.URLField(
        _("ссылка на пост в VK / Telegram"),
        blank=True,
        help_text=_("Ссылка на оригинальный пост в социальных сетях"),
    )
    published_at = models.DateTimeField(
        _("дата и время публикации"),
        null=True,
        blank=True,
        help_text=_("Для немедленной публикации можно оставить пустым — заполнится автоматически"),
    )
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    objects = NewsQuerySet.as_manager()

    class Meta:
        verbose_name = _("новость")
        verbose_name_plural = _("новости")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["category"]),
            models.Index(fields=["organizer"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        # Если статус изменился на PUBLISHED и дата не задана — ставим текущую
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:detail", kwargs={"slug": self.slug})

    def publish(self, moderator=None):
        """Публикация новости штабом / модератором."""
        self.status = self.Status.PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()
        self.save()

        # Оповещение автора новости в Telegram
        if self.author_id:
            from apps.bot.services.notifier import notify_user_async

            msg = (
                f"📰 <b>Ваша новость опубликована!</b>\n\n"
                f"✨ <b>Заголовок:</b> {self.title}\n"
                f"Публикация уже доступна в ленте событий на сайте ШСО ДВФУ."
            )
            notify_user_async(self.author_id, msg)

    def reject(self, moderator=None, comment=""):
        """Возврат новости на доработку с комментарием."""
        self.status = self.Status.RETURNED
        if comment:
            self.moderator_comment = comment
        self.save()

        # Оповещение автора новости в Telegram
        if self.author_id:
            from apps.bot.services.notifier import notify_user_async

            msg = f"⚠️ <b>Новость возвращена на доработку</b>\n\n📝 <b>Заголовок:</b> {self.title}\n"
            if comment:
                msg += f"💬 <b>Комментарий штаба:</b> {comment}\n"
            notify_user_async(self.author_id, msg)


class NewsImage(models.Model):
    """Изображение в галерее новости."""

    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name=_("новость"),
    )
    image = models.ImageField(_("изображение"), upload_to="news/gallery/%Y/%m/")
    caption = models.CharField(_("подпись"), max_length=255, blank=True)
    order = models.PositiveIntegerField(_("порядок"), default=0)

    class Meta:
        verbose_name = _("фотография галереи")
        verbose_name_plural = _("галерея фотографий")
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.news.title} — фото #{self.order or self.pk}"
