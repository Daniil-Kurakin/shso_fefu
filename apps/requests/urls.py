from django.urls import path

from . import views

app_name = "requests"

urlpatterns = [
    path("", views.UserRequestDashboardView.as_view(), name="dashboard"),
    # Панель модерации для администраторов
    path("moderation/", views.AdminModerationView.as_view(), name="moderation"),
    # Помещения
    path("rooms/create/", views.RoomBookingCreateView.as_view(), name="room_create"),
    path("rooms/<int:pk>/", views.RoomBookingDetailView.as_view(), name="room_detail"),
    path("rooms/<int:pk>/cancel/", views.RoomBookingCancelView.as_view(), name="room_cancel"),
    # Пропуска
    path("passes/create/", views.PassRequestCreateView.as_view(), name="pass_create"),
    path("passes/<int:pk>/", views.PassRequestDetailView.as_view(), name="pass_detail"),
    path("passes/<int:pk>/cancel/", views.PassRequestCancelView.as_view(), name="pass_cancel"),
    # Запросы от штаба
    path("hq/", views.HQRequestListView.as_view(), name="hq_list"),
    path("hq/create/", views.HQRequestCreateView.as_view(), name="hq_create"),
    path("hq/<int:pk>/", views.HQRequestDetailView.as_view(), name="hq_detail"),
    path("hq/<int:pk>/edit/", views.HQRequestUpdateView.as_view(), name="hq_edit"),
    path("hq/<int:pk>/delete/", views.HQRequestDeleteView.as_view(), name="hq_delete"),
    path("hq/<int:pk>/respond/", views.HQRequestRespondView.as_view(), name="hq_respond"),
]
