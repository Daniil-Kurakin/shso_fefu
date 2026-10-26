from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Vacancy, VacancyApplication

INPUT_CLS = "form-input"
TEXTAREA_CLS = "form-textarea"
SELECT_CLS = "form-select"
CHECKBOX_CLS = "form-checkbox"


class VacancyForm(forms.ModelForm):
    """Конструктор вакансии / набора со стороны фронтенда."""

    class Meta:
        model = Vacancy
        fields = (
            "title",
            "type",
            "squad",
            "description",
            "requirements",
            "salary",
            "schedule",
            "slots_count",
            "deadline",
            "status",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: Набор вожатых в СПО «Меридиан» на лето 2026"),
                }
            ),
            "type": forms.Select(attrs={"class": SELECT_CLS}),
            "squad": forms.Select(attrs={"class": SELECT_CLS}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": TEXTAREA_CLS,
                    "placeholder": _(
                        "Подробно опишите условия, задачи отряда и что ждёт кандидата..."
                    ),
                }
            ),
            "requirements": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": TEXTAREA_CLS,
                    "placeholder": _(
                        "Возраст 18+, студенческий статус, готовность к обучению и т.д."
                    ),
                }
            ),
            "salary": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("«От 45 000 ₽/мес», «Почасовая» или «Стипендия / стажировка»"),
                }
            ),
            "schedule": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("«Июль-Август 2026, полный день» или «Гибкий график»"),
                }
            ),
            "slots_count": forms.NumberInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: 15 (или пусто, если без лимита)"),
                }
            ),
            "deadline": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
            "status": forms.Select(attrs={"class": SELECT_CLS}),
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

            # Для комсостава отряда тип вакансии заблокирован на вступление в отряд
            self.fields["type"].choices = [
                (Vacancy.Type.JOIN_SQUAD, _("Вступление в студотряд")),
            ]
        else:
            self.fields["squad"].required = False
            self.fields["squad"].help_text = _(
                "Оставьте пустым, если вакансия общештабная или кампусная"
            )


class VacancyApplicationForm(forms.ModelForm):
    """Форма отклика на вакансию или вступление в отряд."""

    data_consent = forms.BooleanField(
        required=True,
        label=_("Я даю согласие на обработку персональных данных"),
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CLS}),
    )

    class Meta:
        model = VacancyApplication
        fields = ("applicant_name", "contact_type", "contact_value", "data_consent")
        widgets = {
            "applicant_name": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Иван Иванов")}
            ),
            "contact_type": forms.Select(attrs={"class": SELECT_CLS}),
            "contact_value": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": "@username, ссылка VK, номер телефона или email",
                }
            ),
        }

    def __init__(self, *args, vacancy=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vacancy = vacancy
        self.user = user

        if self.user and self.user.is_authenticated:
            if not self.initial.get("applicant_name") and self.user.full_name:
                self.fields["applicant_name"].initial = self.user.full_name
            if not self.initial.get("contact_value"):
                self.fields["contact_type"].initial = VacancyApplication.ContactType.EMAIL
                self.fields["contact_value"].initial = self.user.email

    def clean(self):
        cleaned_data = super().clean()
        if self.vacancy and not self.vacancy.is_accepting_applications:
            raise ValidationError(_("Приём заявок на данную вакансию уже завершён."))

        contact_type = cleaned_data.get("contact_type")
        contact_value = cleaned_data.get("contact_value", "").strip()

        if self.vacancy and contact_type and contact_value:
            duplicate = VacancyApplication.objects.filter(
                vacancy=self.vacancy,
                contact_type=contact_type,
                contact_value__iexact=contact_value,
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError(
                    _(
                        "Вы уже подали заявку на эту вакансию с данным контактом. "
                        "Ожидайте ответа штаба."
                    )
                )

        return cleaned_data
