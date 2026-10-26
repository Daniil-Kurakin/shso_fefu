from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    # Вход / выход
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),
    # Регистрация (152-ФЗ, 149-ФЗ)
    path("register/", views.RegisterView.as_view(), name="register"),
    path("register/done/", views.RegistrationDoneView.as_view(), name="registration_done"),
    path("activate/<uidb64>/<token>/", views.ActivateView.as_view(), name="activate"),
    path("resend-activation/", views.ResendActivationView.as_view(), name="resend_activation"),
    # Личный кабинет (витрина профиля)
    path("profile/", views.ProfileView.as_view(), name="profile"),
    # Настройки и редактирование профиля (отдельная страница)
    path("profile/settings/", views.ProfileSettingsView.as_view(), name="settings"),
    path("profile/edit/", views.ProfileSettingsView.as_view(), name="profile_edit"),
    # Портфолио бойца (CRUD)
    path("profile/portfolio/add/", views.PortfolioItemCreateView.as_view(), name="portfolio_add"),
    path(
        "profile/portfolio/<int:pk>/edit/",
        views.PortfolioItemUpdateView.as_view(),
        name="portfolio_edit",
    ),
    path(
        "profile/portfolio/<int:pk>/delete/",
        views.PortfolioItemDeleteView.as_view(),
        name="portfolio_delete",
    ),
    # Смена пароля
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("accounts:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/password_change_done.html",
        ),
        name="password_change_done",
    ),
    # Сброс пароля по email
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/emails/password_reset_email.txt",
            subject_template_name="accounts/emails/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
