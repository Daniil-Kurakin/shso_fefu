from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import BookedPremise, CampusPremise, PassRequest, PassVisitor, RoomBookingRequest

INPUT_CLS = (
    "w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm "
    "focus:ring-2 focus:ring-blue-500 bg-white"
)


class RoomBookingRequestForm(forms.ModelForm):
    """Форма создания заявки на бронирование помещения."""

    class Meta:
        model = RoomBookingRequest
        fields = (
            "room",
            "custom_room",
            "squad",
            "event_name",
            "event_date",
            "start_time",
            "end_time",
            "expected_participants",
            "equipment_required",
        )
        widgets = {
            "room": forms.Select(attrs={"class": INPUT_CLS}),
            "custom_room": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: А826, Коворкинг «Аякс», D504"),
                }
            ),
            "squad": forms.Select(attrs={"class": INPUT_CLS}),
            "event_name": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Собрание отряда / Репетиция")}
            ),
            "event_date": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
            "start_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
            "expected_participants": forms.NumberInput(
                attrs={"class": INPUT_CLS, "min": 1, "max": 500}
            ),
            "equipment_required": forms.Textarea(
                attrs={
                    "class": INPUT_CLS,
                    "rows": 3,
                    "placeholder": _("Проектор, 2 микрофона, флипчарт"),
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Выпадающий список пока оставляем пустым по требованию заказчика
        # (список будет загружен позже)
        if self.data and self.data.get("room"):
            self.fields["room"].queryset = CampusPremise.objects.all()
        elif self.instance and self.instance.room_id:
            self.fields["room"].queryset = CampusPremise.objects.filter(pk=self.instance.room_id)
        else:
            self.fields["room"].queryset = CampusPremise.objects.none()

        self.fields["room"].required = False
        self.fields["room"].empty_label = _("— Список помещений будет доступен позже —")
        self.fields["custom_room"].required = False
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False

        # Если пользователь привязан к отрядам, ограничиваем выбор его отрядами
        if user and not user.is_staff:
            user_squads = user.memberships.filter(is_active=True).values_list("squad_id", flat=True)
            self.fields["squad"].queryset = self.fields["squad"].queryset.filter(id__in=user_squads)

        # Предзаполнение отряда заявителя
        if user:
            user_squad = None
            if hasattr(user, "get_managed_squads"):
                managed = user.get_managed_squads()
                if managed.exists():
                    user_squad = managed.first()
            if not user_squad and hasattr(user, "memberships"):
                m = user.memberships.filter(is_active=True).first()
                if m:
                    user_squad = m.squad
            if user_squad and not self.initial.get("squad"):
                self.initial["squad"] = user_squad.pk

        self.fields["squad"].required = False

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get("event_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        room = cleaned_data.get("room")

        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "end_time", _("Время окончания должно быть строго позже времени начала.")
            )

        if event_date and event_date < timezone.localdate():
            self.add_error("event_date", _("Нельзя выбрать прошедшую дату."))

        if room and event_date and start_time and end_time:
            # Проверка коллизий с одобренными бронями
            conflicts = RoomBookingRequest.objects.filter(
                room=room,
                event_date=event_date,
                status=RoomBookingRequest.Status.APPROVED,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)

            if conflicts.exists():
                c = conflicts.first()
                c_str = f"{c.start_time.strftime('%H:%M')} – {c.end_time.strftime('%H:%M')}"
                self.add_error(
                    "room",
                    _(
                        f"Помещение «{room.name}» уже занято на это время ({c_str}) "
                        f"под «{c.event_name}». Пожалуйста, выберите другое время или аудиторию."
                    ),
                )

        return cleaned_data


class BookedPremiseForm(forms.ModelForm):
    """Форма добавления одной аудитории в заявку на бронирование."""

    class Meta:
        model = BookedPremise
        fields = ("room", "custom_room", "start_time", "end_time")
        widgets = {
            "room": forms.Select(attrs={"class": INPUT_CLS}),
            "custom_room": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Например: А826, D504, Коворкинг «Аякс»"),
                }
            ),
            "start_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": INPUT_CLS, "type": "time", "data-timepicker": "true"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Выпадающий список пока пустой по требованию заказчика (список будет позже)
        if self.data and any(k.endswith("-room") and self.data.get(k) for k in self.data):
            self.fields["room"].queryset = CampusPremise.objects.all()
        elif self.instance and self.instance.room_id:
            self.fields["room"].queryset = CampusPremise.objects.filter(pk=self.instance.room_id)
        else:
            self.fields["room"].queryset = CampusPremise.objects.none()

        self.fields["room"].required = False
        self.fields["room"].empty_label = _("— Список помещений будет доступен позже —")
        self.fields["custom_room"].required = False
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if self.cleaned_data.get("DELETE"):
            return cleaned_data

        room = cleaned_data.get("room")
        custom_room = (cleaned_data.get("custom_room") or "").strip()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        # Если вся строка пустая (например, незаполненная дополнительная форма), пропускаем
        if not room and not custom_room and not start_time and not end_time:
            return cleaned_data

        if not room and not custom_room:
            self.add_error("custom_room", _("Укажите аудиторию или зал."))

        if not start_time:
            self.add_error("start_time", _("Укажите время начала."))

        if not end_time:
            self.add_error("end_time", _("Укажите время окончания."))

        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "end_time", _("Время окончания должно быть строго позже времени начала.")
            )

        return cleaned_data


BookedPremiseFormSet = inlineformset_factory(
    RoomBookingRequest,
    BookedPremise,
    form=BookedPremiseForm,
    extra=1,
    can_delete=True,
)


class PassRequestForm(forms.ModelForm):
    """Форма создания заявки на пропуск."""

    data_consent = forms.BooleanField(
        required=True,
        label=_("Подтверждаю согласие субъектов ПДн на обработку данных (152-ФЗ)"),
        widget=forms.CheckboxInput(
            attrs={"class": "w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-gray-300"}
        ),
    )

    class Meta:
        model = PassRequest
        fields = (
            "squad",
            "title",
            "pass_type",
            "visit_date",
            "visit_end_date",
            "entry_point",
            "car_model",
            "car_number",
            "official_note",
            "data_consent",
        )
        widgets = {
            "squad": forms.Select(attrs={"class": INPUT_CLS}),
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLS,
                    "placeholder": _("Школа комсостава / Приглашённый лектор"),
                }
            ),
            "pass_type": forms.Select(attrs={"class": INPUT_CLS}),
            "visit_date": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
            "visit_end_date": forms.DateInput(attrs={"class": INPUT_CLS, "type": "date"}),
            "entry_point": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Северные ворота / КПП корпус А")}
            ),
            "car_model": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Lada Vesta")}
            ),
            "car_number": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("А123ВС 125")}
            ),
            "official_note": forms.FileInput(attrs={"class": INPUT_CLS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and not user.is_staff:
            user_squads = user.memberships.filter(is_active=True).values_list("squad_id", flat=True)
            self.fields["squad"].queryset = self.fields["squad"].queryset.filter(id__in=user_squads)

        # Предзаполнение отряда заявителя
        if user:
            user_squad = None
            if hasattr(user, "get_managed_squads"):
                managed = user.get_managed_squads()
                if managed.exists():
                    user_squad = managed.first()
            if not user_squad and hasattr(user, "memberships"):
                m = user.memberships.filter(is_active=True).first()
                if m:
                    user_squad = m.squad
            if user_squad and not self.initial.get("squad"):
                self.initial["squad"] = user_squad.pk

        self.fields["squad"].required = False

    def clean(self):
        cleaned_data = super().clean()
        visit_date = cleaned_data.get("visit_date")
        visit_end_date = cleaned_data.get("visit_end_date")
        pass_type = cleaned_data.get("pass_type")
        car_number = cleaned_data.get("car_number")

        if visit_date and visit_date < timezone.localdate():
            self.add_error("visit_date", _("Дата визита не может быть в прошлом."))

        if visit_date and visit_end_date and visit_end_date < visit_date:
            self.add_error(
                "visit_end_date", _("Дата окончания визита не может быть раньше даты начала.")
            )

        if pass_type == PassRequest.PassType.VEHICLE and not car_number:
            self.add_error(
                "car_number",
                _("Для транспортного пропуска необходимо указать госномер автомобиля."),
            )

        return cleaned_data


class PassVisitorForm(forms.ModelForm):
    """Форма добавления одного посетителя."""

    class Meta:
        model = PassVisitor
        fields = ("full_name", "document_type", "document_data", "organization", "phone")
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("Иванов Иван Иванович")}
            ),
            "document_type": forms.Select(attrs={"class": INPUT_CLS}),
            "document_data": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("0515 123456")}
            ),
            "organization": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("ВГУЭС / г. Владивосток")}
            ),
            "phone": forms.TextInput(
                attrs={"class": INPUT_CLS, "placeholder": _("+7 (999) 000-00-00")}
            ),
        }


PassVisitorFormSet = inlineformset_factory(
    PassRequest,
    PassVisitor,
    form=PassVisitorForm,
    extra=1,
    can_delete=True,
)
