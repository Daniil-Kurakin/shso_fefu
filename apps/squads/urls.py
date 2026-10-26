from django.urls import path

from . import views

app_name = "squads"

urlpatterns = [
    path("", views.SquadListView.as_view(), name="list"),
    path("create/", views.SquadCreateView.as_view(), name="create"),
    path("<str:slug>/", views.SquadDetailView.as_view(), name="detail"),
    path("<str:slug>/edit/", views.SquadRevisionCreateView.as_view(), name="revision_create"),
    path("<str:slug>/transfer/", views.SquadTransferCreateView.as_view(), name="transfer_create"),
    path("<str:slug>/members/add/", views.SquadMemberAddView.as_view(), name="member_add"),
]
