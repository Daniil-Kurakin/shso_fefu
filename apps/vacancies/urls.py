from django.urls import path

from . import views

app_name = "vacancies"

urlpatterns = [
    path("", views.VacancyListView.as_view(), name="list"),
    path("create/", views.VacancyCreateView.as_view(), name="create"),
    path("<str:slug>/edit/", views.VacancyUpdateView.as_view(), name="edit"),
    path("<str:slug>/", views.VacancyDetailView.as_view(), name="detail"),
]
