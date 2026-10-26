from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Membership, Position, Squad, SquadPageRevision, SquadTransferRequest

INPUT_CLS = "form-input"
SELECT_CLS = "form-select"
FILE_CLS = "form-file"
CHECKBOX_CLS = "form-checkbox"


class SquadForm(forms.ModelForm):
    """Конструктор создания и редактирования отряда штабом."""

    class Meta:
        model = Squad
        fields = (
            "name",
            "direction",
            "founding_year",
            "motto",
            "description",
            "achievements",
            "contact_url",
            "is_recruiting",
            "logo",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Студенческий педагогический отряд «Импульс»"),
                }
            ),
            "direction": forms.Select(attrs={"class": SELECT_CLS}),
            "founding_year": forms.NumberInput(attrs={"class": INPUT_CLS, "placeholder": "2015"}),
            "motto": forms.TextInput(attrs={"class": INPUT_CLS, "placeholder": _("Девиз отряда")}),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": INPUT_CLS,
                    "placeholder": _(
                        "Подробное описание отряда, история, специфика целины и традиции..."
                    ),
                }
            ),
            "achievements": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": INPUT_CLS,
                    "placeholder": _("Например: 2025 г. — Лучший отряд ШСО ДВФУ"),
                }
            ),
            "contact_url": forms.URLInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": "https://vk.com/squad_name",
                }
            ),
            "is_recruiting": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
            "logo": forms.FileInput(attrs={"class": FILE_CLS, "accept": "image/*"}),
        }


class SquadMemberAddForm(forms.ModelForm):
    """Форма добавления нового бойца в отряд комсоставом или штабом."""

    class Meta:
        model = Membership
        fields = ("user", "position", "start_date")
        widgets = {
            "user": forms.Select(attrs={"class": SELECT_CLS}),
            "position": forms.Select(attrs={"class": SELECT_CLS}),
            "start_date": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
        }

    def __init__(self, *args, squad=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.squad = squad
        user_model = get_user_model()
        active_user_ids = Membership.objects.filter(is_active=True).values_list(
            "user_id", flat=True
        )
        self.fields["user"].queryset = (
            user_model.objects.filter(is_active=True)
            .exclude(id__in=active_user_ids)
            .order_by("full_name", "email")
        )
        self.fields["user"].label_from_instance = lambda u: (
            f"{u.get_full_name()} ({u.email})" if u.get_full_name() else u.email
        )
        self.fields["position"].queryset = Position.objects.all().order_by("order", "name")


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
            "is_recruiting": forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
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
