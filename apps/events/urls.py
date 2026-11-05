from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.CalendarView.as_view(), name="calendar"),
    path("create/", views.EventCreateView.as_view(), name="create"),
    path("<int:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.EventUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.EventDeleteView.as_view(), name="delete"),
    path("<int:pk>/export/ics/", views.EventICalExportView.as_view(), name="export_ics"),
]
