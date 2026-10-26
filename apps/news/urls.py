from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.NewsListView.as_view(), name="list"),
    path("create/", views.NewsCreateView.as_view(), name="create"),
    path("<str:slug>/edit/", views.NewsUpdateView.as_view(), name="edit"),
    path("<str:slug>/", views.NewsDetailView.as_view(), name="detail"),
]
