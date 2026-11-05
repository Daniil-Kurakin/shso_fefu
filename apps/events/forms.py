from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event

INPUT_CLS = (
    "w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm "
    "focus:ring-2 focus:ring-blue-500 bg-white"
)


class EventForm(forms.ModelForm):
    """Форма создания и редактирования события календаря комсоставом штаба."""

    class Meta:
        model = Event
        fields = (
            "title",
            "category",
            "organizer",
            "event_date",
            "start_time",
            "end_time",
            "location",
            "description",
            "image",
            "url",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Название события (например: Спартакиада ШСО ДВФУ)"),
                }
            ),
            "category": forms.Select(attrs={"class": INPUT_CLS}),
            "organizer": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Организатор (например: ШСО ДВФУ, СПО «Лав»)"),
                }
            ),
            "event_date": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
            "start_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
            "location": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Локация (например: Корпус S, Стадион, ауд. А826)"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": INPUT_CLS,
                    "rows": 5,
                    "placeholder": _("Подробная программа, расписание и условия участия..."),
                }
            ),
            "url": forms.URLInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": "https://vk.com/... или форма регистрации",
                }
            ),
        }
