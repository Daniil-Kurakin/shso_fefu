from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import VacancyApplication

INPUT_CLS = (
    "w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm "
    "focus:ring-2 focus:ring-blue-500 bg-white"
)


class VacancyApplicationForm(forms.ModelForm):
    """Форма отклика на вакансию или вступление в отряд."""

    data_consent = forms.BooleanField(
        required=True,
        label=_("Я даю согласие на обработку персональных данных"),
        widget=forms.CheckboxInput(
            attrs={"class": "w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-gray-300"}
        ),
    )

    class Meta:
        model = VacancyApplication
        fields = ("applicant_name", "contact_type", "contact_value", "data_consent")
        widgets = {
            "applicant_name": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Иван Иванов")}
            ),
            "contact_type": forms.Select(attrs={"class": INPUT_CLS}),
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
