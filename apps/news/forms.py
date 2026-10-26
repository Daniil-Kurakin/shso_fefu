from django import forms
from django.utils.translation import gettext_lazy as _

from .models import News

FORM_INPUT_CSS = (
    "block w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm "
    "focus:ring-2 focus:ring-blue-500 focus:outline-none transition bg-white"
)
FORM_TEXTAREA_CSS = (
    "block w-full px-4 py-3 rounded-xl border border-gray-300 text-sm "
    "focus:ring-2 focus:ring-blue-500 focus:outline-none transition bg-white"
)


class NewsForm(forms.ModelForm):
    """Конструктор новости: добавление и редактирование события со стороны фронтенда."""

    class Meta:
        model = News
        fields = [
            "title",
            "category",
            "organizer",
            "squad",
            "lead",
            "content",
            "cover",
            "source_url",
            "status",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": _("Например: Открытие третьего трудового семестра 2026"),
                    "class": FORM_INPUT_CSS,
                }
            ),
            "category": forms.Select(attrs={"class": FORM_INPUT_CSS}),
            "organizer": forms.Select(attrs={"class": FORM_INPUT_CSS}),
            "squad": forms.Select(attrs={"class": FORM_INPUT_CSS}),
            "lead": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _(
                        "Краткий анонс новости для отображения в ленте и превью карточки..."
                    ),
                    "class": FORM_TEXTAREA_CSS,
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 10,
                    "placeholder": _(
                        "Подробный текст новости. Поддерживается форматирование и абзацы."
                    ),
                    "class": FORM_TEXTAREA_CSS,
                }
            ),
            "cover": forms.FileInput(attrs={"class": FORM_INPUT_CSS, "accept": "image/*"}),
            "source_url": forms.URLInput(
                attrs={"placeholder": "https://vk.com/wall-...", "class": FORM_INPUT_CSS}
            ),
            "status": forms.Select(attrs={"class": FORM_INPUT_CSS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user and not user.is_hq_staff:
            managed_squads = user.get_managed_squads()
            self.fields["squad"].queryset = managed_squads
            self.fields["squad"].required = True
            if managed_squads.count() == 1:
                self.fields["squad"].initial = managed_squads.first()

            # Для комсостава отряда ограничиваем доступные статусы
            self.fields["status"].choices = [
                (News.Status.DRAFT, _("Черновик")),
                (News.Status.PENDING, _("Отправить на согласование куратору")),
            ]
        else:
            self.fields["squad"].required = False
            self.fields["squad"].help_text = _(
                "Оставьте пустым, если новость от лица всего Штаба ДВФУ"
            )
