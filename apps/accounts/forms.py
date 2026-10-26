import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User

# Список запрещённых доменов одноразовых почтовых сервисов (борьба со спамом и фишингом)
DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "throwawaymail.com",
    "trashmail.com",
    "yopmail.com",
}

INPUT_CSS = "form-input"
INPUT_WITH_ACTION_CSS = "form-input pr-11"
CHECKBOX_CSS = "form-checkbox mt-1 cursor-pointer"


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class RegistrationForm(forms.Form):
    """
    Форма регистрации нового пользователя.
    Полностью соответствует законодательству РФ:
    - 152-ФЗ «О персональных данных»: явное согласие с фиксацией аудита;
    - 149-ФЗ (в ред. 406-ФЗ): регистрация с подтверждением владения email;
    - Рекомендации ФСТЭК: стойкие пароли, валидаторы Django;
    - Honeypot для защиты от спам-ботов без раздражающих капч.
    """

    full_name = forms.CharField(
        label=_("ФИО"),
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Иванов Иван Иванович"),
                "autocomplete": "name",
                "class": INPUT_CSS,
            }
        ),
        help_text=_("Укажите фамилию, имя и отчество (при наличии)"),
    )

    email = forms.EmailField(
        label=_("Электронная почта"),
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "name@dvfu.ru или user@yandex.ru",
                "autocomplete": "email",
                "class": INPUT_CSS,
            }
        ),
        help_text=_(
            "Рекомендуется использовать корпоративную почту ДВФУ (@dvfu.ru) "
            "или отечественные сервисы (Яндекс, Mail.ru, VK)."
        ),
    )

    phone = forms.CharField(
        label=_("Номер телефона"),
        max_length=25,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "+7 (999) 000-00-00",
                "autocomplete": "tel",
                "class": INPUT_CSS,
            }
        ),
        help_text=_("Необходим комсоставу для оперативной связи с вами"),
    )

    password = forms.CharField(
        label=_("Пароль"),
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": INPUT_WITH_ACTION_CSS,
            }
        ),
        help_text=_("Минимум 8 символов. Не используйте слишком простые пароли."),
    )

    password_confirm = forms.CharField(
        label=_("Подтверждение пароля"),
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": INPUT_WITH_ACTION_CSS,
            }
        ),
        help_text=_("Повторите введённый выше пароль"),
    )

    consent_personal_data = forms.BooleanField(
        label=_(
            "Я подтверждаю, что ознакомлен(а) с Политикой обработки персональных данных "
            "и Пользовательским соглашением, и даю согласие на обработку моих персональных "
            "данных в соответствии с 152-ФЗ."
        ),
        required=True,
        error_messages={
            "required": _(
                "Для регистрации на сайте необходимо дать согласие на обработку "
                "персональных данных (152-ФЗ)."
            )
        },
        widget=forms.CheckboxInput(attrs={"class": CHECKBOX_CSS}),
    )

    # Поле-ловушка (Honeypot): скрыто от людей, заполняется ботами
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
        label="",
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        domain = email.split("@")[-1] if "@" in email else ""

        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise forms.ValidationError(
                _(
                    "Регистрация через сервисы одноразовой почты запрещена. "
                    "Пожалуйста, укажите постоянный email."
                )
            )

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _(
                    "Пользователь с таким email уже зарегистрирован. "
                    "Попробуйте войти или восстановить пароль."
                )
            )

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return ""

        digits = re.sub(r"[^\d+]", "", phone)
        if len(re.sub(r"\D", "", digits)) < 10:
            raise forms.ValidationError(_("Введите корректный номер телефона (не менее 10 цифр)."))
        return phone

    def clean_consent_personal_data(self):
        consent = self.cleaned_data.get("consent_personal_data")
        if not consent:
            raise forms.ValidationError(
                _(
                    "Для создания учетной записи необходимо предоставить согласие "
                    "на обработку персональных данных (152-ФЗ)."
                )
            )
        return consent

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("website"):
            raise forms.ValidationError(_("Ошибка отправки формы."))

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error("password_confirm", _("Введённые пароли не совпадают."))
            else:
                temp_user = User(
                    email=cleaned_data.get("email", "test@example.com"),
                    full_name=cleaned_data.get("full_name", ""),
                )
                try:
                    password_validation.validate_password(password, user=temp_user)
                except forms.ValidationError as error:
                    self.add_error("password", error)

        return cleaned_data


class ResendActivationForm(forms.Form):
    """Форма повторной отправки письма с активацией."""

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@example.com",
                "autocomplete": "email",
                "class": INPUT_CSS,
            }
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
