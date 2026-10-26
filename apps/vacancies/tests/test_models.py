from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.vacancies.models import Vacancy, VacancyApplication


@pytest.mark.django_db
class TestVacancyModel:
    def test_create_and_str(self):
        vacancy = Vacancy.objects.create(
            title="Вожатый в летний лагерь",
            description="Работа летом 2026",
            type=Vacancy.Type.JOIN_SQUAD,
        )
        assert "Вожатый в летний лагерь" in str(vacancy)
        assert vacancy.slug == "вожатый-в-летний-лагерь"
        assert vacancy.is_accepting_applications is True

    def test_open_queryset_and_deadline(self):
        today = timezone.now().date()

        # Вакансия без дедлайна открыта
        v_no_deadline = Vacancy.objects.create(
            title="Вакансия 1",
            description="desc",
            status=Vacancy.Status.OPEN,
        )
        # Вакансия с дедлайном в будущем открыта
        v_future = Vacancy.objects.create(
            title="Вакансия 2",
            description="desc",
            status=Vacancy.Status.OPEN,
            deadline=today + timedelta(days=10),
        )
        # Вакансия с истекшим дедлайном закрыта
        v_expired = Vacancy.objects.create(
            title="Вакансия 3",
            description="desc",
            status=Vacancy.Status.OPEN,
            deadline=today - timedelta(days=1),
        )
        # Вакансия в черновике закрыта
        v_draft = Vacancy.objects.create(
            title="Вакансия 4",
            description="desc",
            status=Vacancy.Status.DRAFT,
        )
        # Вакансия в архиве закрыта
        v_closed = Vacancy.objects.create(
            title="Вакансия 5",
            description="desc",
            status=Vacancy.Status.CLOSED,
        )

        open_qs = Vacancy.objects.open()
        assert v_no_deadline in open_qs
        assert v_future in open_qs
        assert v_expired not in open_qs
        assert v_draft not in open_qs
        assert v_closed not in open_qs

        assert v_future.is_accepting_applications is True
        assert v_expired.is_accepting_applications is False
        assert v_closed.is_accepting_applications is False


@pytest.mark.django_db
class TestVacancyApplicationModel:
    def test_create_application_and_strip(self):
        vacancy = Vacancy.objects.create(
            title="Аниматор",
            description="Работа на кампусе",
            type=Vacancy.Type.CAMPUS_JOB,
        )
        app = VacancyApplication.objects.create(
            vacancy=vacancy,
            applicant_name="Иван Петров",
            contact_type=VacancyApplication.ContactType.TELEGRAM,
            contact_value="  @ivan_petrov  ",
            data_consent=True,
        )
        assert app.contact_value == "@ivan_petrov"
        assert "Иван Петров" in str(app)
        assert vacancy.applications_count == 1

    def test_unique_contact_constraint(self):
        vacancy = Vacancy.objects.create(
            title="Строитель",
            description="Работа",
        )
        VacancyApplication.objects.create(
            vacancy=vacancy,
            applicant_name="Иван",
            contact_type=VacancyApplication.ContactType.EMAIL,
            contact_value="ivan@example.com",
            data_consent=True,
        )

        # Тот же email в разном регистре должен вызывать IntegrityError
        with pytest.raises(IntegrityError):
            VacancyApplication.objects.create(
                vacancy=vacancy,
                applicant_name="Иван Другой",
                contact_type=VacancyApplication.ContactType.EMAIL,
                contact_value="IVAN@EXAMPLE.COM",
                data_consent=True,
            )
