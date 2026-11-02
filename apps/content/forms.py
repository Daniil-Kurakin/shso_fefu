from django import forms
from django.utils.translation import gettext_lazy as _

from .models import CustomPage, FAQItem, GlossaryTerm, KnowledgeArticle, PageBlock

INPUT_CLS = "form-input"
TEXTAREA_CLS = "form-textarea"
SELECT_CLS = "form-select"
CHECKBOX_CLS = "form-checkbox"
FILE_CLS = "form-file"


class KnowledgeArticleForm(forms.ModelForm):
    """Конструктор статьи базы знаний."""

    class Meta:
        model = KnowledgeArticle
        fields = (
            "category",
            "title",
            "summary",
            "content",
            "attachment",
            "pinned",
            "is_published",
        )
        widgets = {
            "category": forms.Select(attrs={"class": SELECT_CLS}),
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Регламент оформления пропусков на кампус ДВФУ"),
                }
            ),
            "summary": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": TEXTAREA_CLS,
                    "placeholder": _("Краткая выжимка статьи для карточки и поиска..."),
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 10,
                    "class": TEXTAREA_CLS,
                    "placeholder": _(
                        "Текст статьи или инструкции. Поддерживаются абзацы и списки."
                    ),
                }
            ),
            "attachment": forms.FileInput(attrs={"class": FILE_CLS}),
            "pinned": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
            "is_published": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
        }


class FAQItemForm(forms.ModelForm):
    """Конструктор вопроса-ответа FAQ."""

    class Meta:
        model = FAQItem
        fields = ("category", "question", "answer", "order", "is_published")
        widgets = {
            "category": forms.Select(attrs={"class": SELECT_CLS}),
            "question": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Как вступить в строительный отряд?"),
                }
            ),
            "answer": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": TEXTAREA_CLS,
                    "placeholder": _("Подробный и понятный ответ на вопрос..."),
                }
            ),
            "order": forms.NumberInput(attrs={"class": INPUT_CLS}),
            "is_published": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
        }


class GlossaryTermForm(forms.ModelForm):
    """Конструктор термина глоссария."""

    class Meta:
        model = GlossaryTerm
        fields = ("term", "definition", "synonyms")
        widgets = {
            "term": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Целина, Боёвка, Строевка"),
                }
            ),
            "definition": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": TEXTAREA_CLS,
                    "placeholder": _("Толкование и значение термина в отрядном движении..."),
                }
            ),
            "synonyms": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Синонимы через запятую (например: целинка, куртка)"),
                }
            ),
        }


class CustomPageForm(forms.ModelForm):
    """Форма редактирования метаданных страницы в конструкторе."""

    class Meta:
        model = CustomPage
        fields = ("title", "slug", "summary", "is_published")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: История отрядного движения ДВФУ"),
                }
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("history (латинские буквы, цифры, дефис)"),
                }
            ),
            "summary": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": TEXTAREA_CLS,
                    "placeholder": _("Краткое резюме / SEO meta description..."),
                }
            ),
            "is_published": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
        }


class PageBlockForm(forms.ModelForm):
    """Форма блока страницы в конструкторе."""

    class Meta:
        model = PageBlock
        fields = (
            "block_type",
            "title",
            "subtitle",
            "content",
            "image",
            "button_text",
            "button_url",
            "order",
            "is_active",
        )
        widgets = {
            "block_type": forms.Select(attrs={"class": SELECT_CLS}),
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Заголовок секции / блока"),
                }
            ),
            "subtitle": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Подзаголовок / пояснение к блоку"),
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": TEXTAREA_CLS,
                    "placeholder": _(
                        "Текст, параграфы или разметка. "
                        "Для карточек: Заголовок | Текст | Ссылка. "
                        "Для FAQ: Вопрос | Ответ."
                    ),
                }
            ),
            "image": forms.FileInput(attrs={"class": FILE_CLS}),
            "button_text": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Подробнее"),
                }
            ),
            "button_url": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: /squads/ или https://..."),
                }
            ),
            "order": forms.NumberInput(attrs={"class": INPUT_CLS, "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
        }


PageBlockFormSet = forms.inlineformset_factory(
    CustomPage,
    PageBlock,
    form=PageBlockForm,
    extra=1,
    can_delete=True,
)
