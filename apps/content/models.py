import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
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
        try:
            pinned = cls.objects.filter(is_active=True, pinned_date=today)
            quote = pinned.filter(language=lang).first() or pinned.filter(language="ru").first()

            # 2. Если закреплённой нет, выбираем детерминированно из банка активных цитат
            if not quote:
                quotes = list(cls.objects.filter(is_active=True, language=lang))
                if not quotes and lang != "ru":
                    quotes = list(cls.objects.filter(is_active=True, language="ru"))

                if quotes:
                    index = today.toordinal() % len(quotes)
                    quote = quotes[index]
        except DatabaseError:
            return None

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
        except (cls.DoesNotExist, DatabaseError):
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
        except (cls.DoesNotExist, DatabaseError):
            obj = None
        cache.set(cache_key, obj, timeout=3600)
        return obj


class KnowledgeCategory(models.Model):
    """Категория статей базы знаний."""

    title = models.CharField(_("название категории"), max_length=150)
    slug = models.SlugField(_("URL"), max_length=150, unique=True, allow_unicode=True)
    icon = models.CharField(_("иконка (эмодзи)"), max_length=10, default="📚")
    description = models.TextField(_("описание категории"), blank=True)
    order = models.PositiveIntegerField(_("порядок"), default=0)

    class Meta:
        verbose_name = _("категория базы знаний")
        verbose_name_plural = _("категории базы знаний")
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.icon} {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("content:knowledge_category", kwargs={"category_slug": self.slug})


class KnowledgeArticle(models.Model):
    """Статья базы знаний или регламент."""

    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.CASCADE,
        related_name="articles",
        verbose_name=_("категория"),
    )
    title = models.CharField(_("название статьи"), max_length=200)
    slug = models.SlugField(_("URL"), max_length=200, unique=True, allow_unicode=True)
    summary = models.CharField(
        _("краткое описание"),
        max_length=350,
        help_text=_("Выжимка для карточки статьи и поисковой выдачи"),
    )
    content = models.TextField(_("текст статьи"))
    attachment = models.FileField(
        _("прикрепленный файл / бланк"),
        upload_to="content/knowledge/%Y/",
        blank=True,
        null=True,
        help_text=_("Шаблон заявления, регламент или памятка"),
    )
    pinned = models.BooleanField(
        _("закрепить в топе"),
        default=False,
        help_text=_("Закреплённые статьи выводятся первыми в категории и на главной базы знаний"),
    )
    is_published = models.BooleanField(_("опубликована"), default=True)
    views_count = models.PositiveIntegerField(_("просмотров"), default=0)
    order = models.PositiveIntegerField(_("порядок"), default=0)
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    class Meta:
        verbose_name = _("статья базы знаний")
        verbose_name_plural = _("статьи базы знаний")
        ordering = ["-pinned", "order", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "content:knowledge_detail",
            kwargs={"category_slug": self.category.slug, "slug": self.slug},
        )


class FAQCategory(models.Model):
    """Категория вопросов и ответов."""

    title = models.CharField(_("название категории"), max_length=150)
    slug = models.SlugField(_("URL"), max_length=150, unique=True, allow_unicode=True)
    order = models.PositiveIntegerField(_("порядок"), default=0)

    class Meta:
        verbose_name = _("категория FAQ")
        verbose_name_plural = _("категории FAQ")
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class FAQItem(models.Model):
    """Часто задаваемый вопрос (FAQ)."""

    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("категория"),
    )
    question = models.CharField(_("вопрос"), max_length=255)
    answer = models.TextField(_("ответ"))
    order = models.PositiveIntegerField(_("порядок"), default=0)
    is_published = models.BooleanField(_("опубликован"), default=True)
    created_at = models.DateTimeField(_("создан"), auto_now_add=True)

    class Meta:
        verbose_name = _("вопрос FAQ")
        verbose_name_plural = _("вопросы и ответы (FAQ)")
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class GlossaryTerm(models.Model):
    """Термин отрядного глоссария / сленга."""

    term = models.CharField(_("термин / понятие"), max_length=150, unique=True)
    slug = models.SlugField(_("URL"), max_length=150, unique=True, blank=True, allow_unicode=True)
    letter = models.CharField(
        _("буква алфавита"), max_length=2, db_index=True, blank=True, editable=False
    )
    definition = models.TextField(_("определение / толкование"))
    synonyms = models.CharField(
        _("синонимы / альтернативные названия"),
        max_length=200,
        blank=True,
        help_text=_("Например: «Строевка, Целинка»"),
    )
    order = models.PositiveIntegerField(_("порядок"), default=0)

    class Meta:
        verbose_name = _("отрядный термин")
        verbose_name_plural = _("глоссарий студотрядов")
        ordering = ["letter", "term"]

    def __str__(self):
        return self.term

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.term, allow_unicode=True)
        clean_term = self.term.strip()
        if clean_term:
            first_char = clean_term[0].upper()
            if first_char in {'"', "«", "“"} and len(clean_term) > 1:
                first_char = clean_term[1].upper()
            self.letter = first_char
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not self.slug and self.term:
            self.slug = slugify(self.term, allow_unicode=True)
        clean_term = (self.term or "").strip()
        if clean_term:
            first_char = clean_term[0].upper()
            if first_char in {'"', "«", "“"} and len(clean_term) > 1:
                first_char = clean_term[1].upper()
            self.letter = first_char


class CustomPage(models.Model):
    """Кастомная страница сайта, создаваемая и настраиваемая через конструктор страниц."""

    title = models.CharField(_("заголовок страницы"), max_length=200)
    slug = models.SlugField(_("URL (slug)"), max_length=200, unique=True, allow_unicode=True)
    summary = models.CharField(
        _("краткое описание / SEO"),
        max_length=350,
        blank=True,
        help_text=_("Используется для поисковой оптимизации (meta description) и карточек"),
    )
    is_published = models.BooleanField(_("опубликована"), default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_pages",
        verbose_name=_("автор"),
    )
    created_at = models.DateTimeField(_("создана"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлена"), auto_now=True)

    class Meta:
        verbose_name = _("страница")
        verbose_name_plural = _("страницы сайта (конструктор)")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("content:page_detail", kwargs={"slug": self.slug})

    def ordered_blocks(self):
        return self.blocks.filter(is_active=True).order_by("order", "id")


class PageBlock(models.Model):
    """Смысловой блок/секция внутри настраиваемой страницы конструктора."""

    class BlockType(models.TextChoices):
        HERO = "hero", _("Баннер / Главный экран")
        TEXT = "text", _("Текстовый блок / Статья")
        CARDS = "cards", _("Сетка карточек / Особенности")
        ACCORDION = "accordion", _("Аккордеон / FAQ")
        CTA = "cta", _("Баннер с кнопкой (CTA)")
        QUOTE = "quote", _("Цитата / Врезка")
        GALLERY = "gallery", _("Изображение / Медиа")

    page = models.ForeignKey(
        CustomPage,
        on_delete=models.CASCADE,
        related_name="blocks",
        verbose_name=_("страница"),
    )
    block_type = models.CharField(
        _("тип блока"),
        max_length=20,
        choices=BlockType.choices,
        default=BlockType.TEXT,
    )
    title = models.CharField(_("заголовок"), max_length=255, blank=True)
    subtitle = models.CharField(_("подзаголовок / описание"), max_length=255, blank=True)
    content = models.TextField(
        _("содержимое"),
        blank=True,
        help_text=_(
            "Для текста: текст/абзацы. Для карточек: строка вида «Заголовок | Описание | Ссылка». "
            "Для аккордеона: строка вида «Вопрос | Ответ»."
        ),
    )
    image = models.ImageField(
        _("изображение"),
        upload_to="pages/blocks/%Y/",
        blank=True,
        null=True,
    )
    button_text = models.CharField(_("текст кнопки"), max_length=100, blank=True)
    button_url = models.CharField(_("ссылка кнопки"), max_length=255, blank=True)
    order = models.PositiveIntegerField(_("порядок"), default=0)
    is_active = models.BooleanField(_("активен"), default=True)

    class Meta:
        verbose_name = _("блок страницы")
        verbose_name_plural = _("блоки страницы")
        ordering = ["order", "id"]

    def __str__(self):
        label = self.title or self.get_block_type_display()
        return f"{self.page.title} — [{self.get_block_type_display()}] {label}"

    def parsed_cards(self):
        """Парсит content в список карточек [title, text, url]."""
        items = []
        for line in (self.content or "").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            item_title = parts[0]
            item_text = parts[1] if len(parts) > 1 else ""
            item_url = parts[2] if len(parts) > 2 else ""
            items.append({"title": item_title, "text": item_text, "url": item_url})
        return items

    def parsed_accordion(self):
        """Парсит content в список вопросов-ответов [question, answer]."""
        items = []
        for line in (self.content or "").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            q = parts[0]
            a = parts[1] if len(parts) > 1 else ""
            items.append({"question": q, "answer": a})
        return items
