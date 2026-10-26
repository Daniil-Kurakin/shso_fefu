from django.urls import path

from . import views

app_name = "squads"

urlpatterns = [
    path("", views.SquadListView.as_view(), name="list"),
    path("<str:slug>/", views.SquadDetailView.as_view(), name="detail"),
    path("<str:slug>/edit/", views.SquadRevisionCreateView.as_view(), name="revision_create"),
    path("<str:slug>/transfer/", views.SquadTransferCreateView.as_view(), name="transfer_create"),
]
