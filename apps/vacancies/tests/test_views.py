import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from apps.accounts.models import User
from apps.vacancies.admin import VacancyAdmin, VacancyApplicationAdmin
from apps.vacancies.models import Vacancy, VacancyApplication


class DummyMessageStorage:
    def __init__(self, request=None):
        self.messages = []

    def add(self, level, message, extra_tags=""):
        self.messages.append(message)

    def __iter__(self):
        return iter(self.messages)


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="test_applicant@example.com",
        password="secretpassword123",
        full_name="Иван Иванов",
    )


@pytest.fixture
def open_vacancy(db):
    return Vacancy.objects.create(
        title="Официант в кафе Аякс",
        description="Работа на кампусе со сменным графиком",
        requirements="Ответственность и пунктуальность",
        type=Vacancy.Type.CAMPUS_JOB,
        status=Vacancy.Status.OPEN,
        salary="350 ₽/час",
    )


@pytest.fixture
def closed_vacancy(db):
    return Vacancy.objects.create(
        title="Проводник пассажирского вагона",
        description="Летний семестр 2026",
        status=Vacancy.Status.CLOSED,
    )


@pytest.mark.django_db
class TestVacancyViews:
    def test_vacancy_list_view(self, client, open_vacancy, closed_vacancy):
        url = reverse("vacancies:list")
        response = client.get(url)
        assert response.status_code == 200
        assert open_vacancy.title.encode() in response.content
        assert closed_vacancy.title.encode() not in response.content

    def test_vacancy_list_filters(self, client, open_vacancy):
        squad_vac = Vacancy.objects.create(
            title="Вожатый СПО",
            description="Лагерная смена",
            type=Vacancy.Type.JOIN_SQUAD,
            status=Vacancy.Status.OPEN,
        )

        url = reverse("vacancies:list")
        # Фильтр по campus_job
        res1 = client.get(f"{url}?type=campus_job")
        assert open_vacancy.title.encode() in res1.content
        assert squad_vac.title.encode() not in res1.content

        # Поиск по q
        res2 = client.get(f"{url}?q=Вожатый")
        assert squad_vac.title.encode() in res2.content
        assert open_vacancy.title.encode() not in res2.content

    def test_vacancy_detail_view_get(self, client, open_vacancy):
        url = open_vacancy.get_absolute_url()
        response = client.get(url)
        assert response.status_code == 200
        assert open_vacancy.title.encode() in response.content
        assert "Отправить отклик".encode() in response.content

    def test_vacancy_detail_closed_get(self, client, closed_vacancy):
        url = closed_vacancy.get_absolute_url()
        response = client.get(url)
        assert response.status_code == 200
        assert "Приём откликов закрыт".encode() in response.content

    def test_application_post_guest_success(self, client, open_vacancy):
        url = open_vacancy.get_absolute_url()
        data = {
            "applicant_name": "Пётр Сидоров",
            "contact_type": VacancyApplication.ContactType.TELEGRAM,
            "contact_value": "@sidorov_petr",
            "data_consent": True,
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200

        app = VacancyApplication.objects.get(vacancy=open_vacancy)
        assert app.applicant_name == "Пётр Сидоров"
        assert app.user is None
        assert app.contact_value == "@sidorov_petr"
        assert app.status == VacancyApplication.Status.NEW

    def test_application_post_authenticated_user(self, client, test_user, open_vacancy):
        client.force_login(test_user)
        url = open_vacancy.get_absolute_url()
        data = {
            "applicant_name": "Иван Иванов",
            "contact_type": VacancyApplication.ContactType.EMAIL,
            "contact_value": test_user.email,
            "data_consent": True,
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200

        app = VacancyApplication.objects.get(vacancy=open_vacancy)
        assert app.user == test_user
        assert app.contact_value == test_user.email

    def test_application_post_duplicate_rejected(self, client, open_vacancy):
        url = open_vacancy.get_absolute_url()
        data = {
            "applicant_name": "Иван",
            "contact_type": VacancyApplication.ContactType.VK,
            "contact_value": "vk.com/ivan_id",
            "data_consent": True,
        }
        res1 = client.post(url, data=data, follow=True)
        assert res1.status_code == 200
        assert VacancyApplication.objects.count() == 1

        # Повторный отклик с тем же контактом
        res2 = client.post(url, data=data, follow=True)
        assert res2.status_code == 200
        assert "Вы уже подали заявку на эту вакансию".encode() in res2.content
        assert VacancyApplication.objects.count() == 1

    def test_application_post_to_closed_vacancy(self, client, closed_vacancy):
        url = closed_vacancy.get_absolute_url()
        data = {
            "applicant_name": "Иван",
            "contact_type": VacancyApplication.ContactType.TELEGRAM,
            "contact_value": "@ivan",
            "data_consent": True,
        }
        response = client.post(url, data=data, follow=True)
        assert response.status_code == 200
        assert VacancyApplication.objects.count() == 0


@pytest.mark.django_db
class TestVacancyAdmin:
    def test_admin_export_csv_and_actions(self, rf, open_vacancy):
        admin_obj = VacancyAdmin(Vacancy, site)
        qs = Vacancy.objects.filter(pk=open_vacancy.pk)
        request = rf.get("/admin/vacancies/vacancy/")
        request._messages = DummyMessageStorage(request)

        # Закрытие через admin action
        admin_obj.action_close(request, qs)
        open_vacancy.refresh_from_db()
        assert open_vacancy.status == Vacancy.Status.CLOSED

        # Открытие через admin action
        admin_obj.action_open(request, qs)
        open_vacancy.refresh_from_db()
        assert open_vacancy.status == Vacancy.Status.OPEN

        # Проверка выгрузки в CSV
        app_admin = VacancyApplicationAdmin(VacancyApplication, site)
        app = VacancyApplication.objects.create(
            vacancy=open_vacancy,
            applicant_name="Тест Экспорта",
            contact_type=VacancyApplication.ContactType.TELEGRAM,
            contact_value="@test_export",
            data_consent=True,
        )

        app_qs = VacancyApplication.objects.filter(pk=app.pk)
        csv_response = app_admin.export_as_csv(request, app_qs)
        assert csv_response.status_code == 200
        assert csv_response["Content-Type"] == "text/csv; charset=utf-8-sig"
        assert 'attachment; filename="applications_' in csv_response["Content-Disposition"]
        content = csv_response.content.decode("utf-8-sig")
        assert "Тест Экспорта" in content
        assert "@test_export" in content
