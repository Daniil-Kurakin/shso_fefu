from django.urls import path

from . import views

app_name = "vacancies"

urlpatterns = [
    path("", views.VacancyListView.as_view(), name="list"),
    path("<str:slug>/", views.VacancyDetailView.as_view(), name="detail"),
]
