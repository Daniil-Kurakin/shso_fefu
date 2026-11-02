import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe
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

    class FontFamily(models.TextChoices):
        SANS = "sans", _("Montserrat (Основной текст)")
        HEADING = "heading", _("Coolvetica (Заголовочный)")
        SERIF = "serif", _("С засечками (Serif)")
        MONO = "mono", _("Моноширинный (Mono)")

    class TextSize(models.TextChoices):
        SM = "sm", _("Мелкий (14px)")
        BASE = "base", _("Стандартный (16px)")
        LG = "lg", _("Крупный (18px)")
        XL = "xl", _("Очень крупный (20px)")
        XL2 = "2xl", _("Заголовочный (24px)")
        XL3 = "3xl", _("Большой заголовок (30px)")
        XL4 = "4xl", _("Акцентный заголовок (36px)")

    class TextAlign(models.TextChoices):
        LEFT = "left", _("По левому краю")
        CENTER = "center", _("По центру")
        RIGHT = "right", _("По правому краю")
        JUSTIFY = "justify", _("По ширине")

    class TextColor(models.TextChoices):
        DEFAULT = "default", _("Тёмно-серый (по умолчанию)")
        BLUE = "blue", _("Синий брендовый")
        WHITE = "white", _("Белый")
        MUTED = "muted", _("Приглушённый серый")

    class ImageSize(models.TextChoices):
        SMALL = "small", _("Маленький (~320px)")
        MEDIUM = "medium", _("Средний (~480px)")
        LARGE = "large", _("Крупный (~720px)")
        FULL = "full", _("На всю ширину (100%)")
        ORIGINAL = "original", _("Естественный размер")

    class ImageAlign(models.TextChoices):
        CENTER = "center", _("По центру")
        LEFT = "left", _("Слева")
        RIGHT = "right", _("Справа")

    class ImageRadius(models.TextChoices):
        ROUNDED = "rounded", _("Скругленные углы (16px)")
        FULL = "full", _("Круг / Овал")
        NONE = "none", _("Прямые углы (без скругления)")

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
            "Для текста: текст/абзацы или HTML-разметка. "
            "Для карточек: строка вида «Заголовок | Описание | Ссылка». "
            "Для аккордеона: строка вида «Вопрос | Ответ»."
        ),
    )

    # Настройки оформления текста
    font_family = models.CharField(
        _("шрифт текста"),
        max_length=20,
        choices=FontFamily.choices,
        default=FontFamily.SANS,
        blank=True,
    )
    text_size = models.CharField(
        _("размер текста"),
        max_length=10,
        choices=TextSize.choices,
        default=TextSize.BASE,
        blank=True,
    )
    text_align = models.CharField(
        _("выравнивание текста"),
        max_length=10,
        choices=TextAlign.choices,
        default=TextAlign.LEFT,
        blank=True,
    )
    text_color = models.CharField(
        _("цвет текста"),
        max_length=15,
        choices=TextColor.choices,
        default=TextColor.DEFAULT,
        blank=True,
    )

    # Изображение и настройки его отображения
    image = models.ImageField(
        _("изображение"),
        upload_to="pages/blocks/%Y/",
        blank=True,
        null=True,
    )
    image_size = models.CharField(
        _("размер изображения"),
        max_length=15,
        choices=ImageSize.choices,
        default=ImageSize.MEDIUM,
        blank=True,
    )
    image_align = models.CharField(
        _("выравнивание изображения"),
        max_length=10,
        choices=ImageAlign.choices,
        default=ImageAlign.CENTER,
        blank=True,
    )
    image_radius = models.CharField(
        _("скругление углов фото"),
        max_length=15,
        choices=ImageRadius.choices,
        default=ImageRadius.ROUNDED,
        blank=True,
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

    def save(self, *args, **kwargs):
        if not self.font_family:
            self.font_family = self.FontFamily.SANS
        if not self.text_size:
            self.text_size = self.TextSize.BASE
        if not self.text_align:
            self.text_align = self.TextAlign.LEFT
        if not self.text_color:
            self.text_color = self.TextColor.DEFAULT
        if not self.image_size:
            self.image_size = self.ImageSize.MEDIUM
        if not self.image_align:
            self.image_align = self.ImageAlign.CENTER
        if not self.image_radius:
            self.image_radius = self.ImageRadius.ROUNDED
        super().save(*args, **kwargs)

    def get_font_css(self) -> str:
        """Возвращает CSS-классы шрифта."""
        mapping = {
            self.FontFamily.HEADING: "font-heading uppercase",
            self.FontFamily.SANS: "font-sans",
            self.FontFamily.SERIF: "font-serif",
            self.FontFamily.MONO: "font-mono",
        }
        return mapping.get(self.font_family, "font-sans")

    def get_text_size_css(self) -> str:
        """Возвращает CSS-класс размера шрифта."""
        mapping = {
            self.TextSize.SM: "text-sm",
            self.TextSize.BASE: "text-base",
            self.TextSize.LG: "text-lg",
            self.TextSize.XL: "text-xl",
            self.TextSize.XL2: "text-2xl",
            self.TextSize.XL3: "text-3xl",
            self.TextSize.XL4: "text-4xl",
        }
        return mapping.get(self.text_size, "text-base")

    def get_text_align_css(self) -> str:
        """Возвращает CSS-класс выравнивания текста."""
        mapping = {
            self.TextAlign.LEFT: "text-left",
            self.TextAlign.CENTER: "text-center",
            self.TextAlign.RIGHT: "text-right",
            self.TextAlign.JUSTIFY: "text-justify",
        }
        return mapping.get(self.text_align, "text-left")

    def get_text_color_css(self) -> str:
        """Возвращает CSS-класс цвета текста."""
        mapping = {
            self.TextColor.DEFAULT: "text-gray-800",
            self.TextColor.BLUE: "text-blue-700",
            self.TextColor.WHITE: "text-white",
            self.TextColor.MUTED: "text-gray-500",
        }
        return mapping.get(self.text_color, "text-gray-800")

    def get_image_size_css(self) -> str:
        """Возвращает CSS-класс максимальной ширины изображения."""
        mapping = {
            self.ImageSize.SMALL: "max-w-xs",
            self.ImageSize.MEDIUM: "max-w-md",
            self.ImageSize.LARGE: "max-w-2xl",
            self.ImageSize.FULL: "w-full max-w-full",
            self.ImageSize.ORIGINAL: "max-w-fit",
        }
        return mapping.get(self.image_size, "max-w-md")

    def get_image_align_css(self) -> str:
        """Возвращает CSS-класс выравнивания изображения (margin auto)."""
        mapping = {
            self.ImageAlign.CENTER: "mx-auto",
            self.ImageAlign.LEFT: "mr-auto",
            self.ImageAlign.RIGHT: "ml-auto",
        }
        return mapping.get(self.image_align, "mx-auto")

    def get_image_radius_css(self) -> str:
        """Возвращает CSS-класс скругления углов изображения."""
        mapping = {
            self.ImageRadius.ROUNDED: "rounded-2xl",
            self.ImageRadius.FULL: "rounded-full",
            self.ImageRadius.NONE: "rounded-none",
        }
        return mapping.get(self.image_radius, "rounded-2xl")

    @property
    def rendered_content(self):
        """Рендерит контент: безопасно поддерживает HTML-теги или авто-абзацы."""
        text = self.content or ""
        html_tags = (
            "<p>",
            "<div>",
            "<br>",
            "<span",
            "<h1",
            "<h2",
            "<h3",
            "<ul",
            "<ol",
            "<table>",
        )
        if any(tag in text.lower() for tag in html_tags):
            return mark_safe(text)  # noqa: S308  # Владелец сайта формирует разметку
        return mark_safe(linebreaks(text))  # noqa: S308

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
