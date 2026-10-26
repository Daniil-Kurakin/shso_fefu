from django import forms
from django.utils.translation import gettext_lazy as _

from .models import FAQItem, GlossaryTerm, KnowledgeArticle

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
