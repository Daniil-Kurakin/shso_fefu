from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Position, Squad, SquadPageRevision, SquadTransferRequest

INPUT_CLS = (
    "w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-blue-500"
)
SELECT_CLS = f"{INPUT_CLS} bg-white"
FILE_CLS = (
    "w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 "
    "file:rounded-xl file:border-0 file:text-sm file:font-semibold "
    "file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
)


class SquadPageRevisionForm(forms.ModelForm):
    """Форма редактирования страницы отряда для комсостава."""

    class Meta:
        model = SquadPageRevision
        fields = (
            "motto",
            "description",
            "achievements",
            "contact_url",
            "is_recruiting",
        )
        widgets = {
            "motto": forms.TextInput(attrs={"class": INPUT_CLS, "placeholder": _("Девиз отряда")}),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": INPUT_CLS,
                    "placeholder": _("Подробное описание отряда, история и традиции"),
                }
            ),
            "achievements": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": INPUT_CLS,
                    "placeholder": _("Например: 2025 г. — Лучший СПО Приморского края"),
                }
            ),
            "contact_url": forms.URLInput(
                attrs={"class": INPUT_CLS, "placeholder": "https://vk.com/squad_name"}
            ),
            "is_recruiting": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-gray-300"}
            ),
        }


class SquadTransferRequestForm(forms.ModelForm):
    """Форма подачи заявки на переход бойца между отрядами командиром."""

    class Meta:
        model = SquadTransferRequest
        fields = ("user", "to_squad", "new_position", "document")
        widgets = {
            "user": forms.Select(attrs={"class": SELECT_CLS}),
            "to_squad": forms.Select(attrs={"class": SELECT_CLS}),
            "new_position": forms.Select(attrs={"class": SELECT_CLS}),
            "document": forms.FileInput(attrs={"class": FILE_CLS, "accept": ".pdf,image/*"}),
        }

    def __init__(self, *args, from_squad=None, **kwargs):
        super().__init__(*args, **kwargs)
        if from_squad:
            # Выбираем только активных бойцов исходного отряда
            active_user_ids = from_squad.memberships.filter(is_active=True).values_list(
                "user_id", flat=True
            )
            self.fields["user"].queryset = self.fields["user"].queryset.filter(
                id__in=active_user_ids
            )
            # Исключаем исходный отряд из списка целевых
            self.fields["to_squad"].queryset = Squad.objects.exclude(pk=from_squad.pk)
        self.fields["new_position"].queryset = Position.objects.all()
