from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("contacts/", views.ContactsView.as_view(), name="contacts"),
]
