from django.urls import path

from . import views

app_name = "requests"

urlpatterns = [
    path("", views.UserRequestDashboardView.as_view(), name="dashboard"),
    # Помещения
    path("rooms/create/", views.RoomBookingCreateView.as_view(), name="room_create"),
    path("rooms/<int:pk>/", views.RoomBookingDetailView.as_view(), name="room_detail"),
    path("rooms/<int:pk>/cancel/", views.RoomBookingCancelView.as_view(), name="room_cancel"),
    # Пропуска
    path("passes/create/", views.PassRequestCreateView.as_view(), name="pass_create"),
    path("passes/<int:pk>/", views.PassRequestDetailView.as_view(), name="pass_detail"),
    path("passes/<int:pk>/cancel/", views.PassRequestCancelView.as_view(), name="pass_cancel"),
]
