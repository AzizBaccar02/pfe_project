from django.urls import path
from .views import (
    NotificationCreateAPIView,
    MyNotificationsAPIView,
    MyNotificationDetailAPIView,
    MarkAllNotificationsAsReadAPIView,
    UnreadNotificationsCountAPIView,
)

urlpatterns = [
    path("notifications/", NotificationCreateAPIView.as_view(), name="create-notification"),
    path("notifications/me/", MyNotificationsAPIView.as_view(), name="my-notifications"),
    path("notifications/me/<int:id>/", MyNotificationDetailAPIView.as_view(), name="my-notification-detail"),
    path("notifications/me/read-all/", MarkAllNotificationsAsReadAPIView.as_view(), name="mark-all-notifications-read"),
    path("notifications/me/unread-count/", UnreadNotificationsCountAPIView.as_view(), name="my-unread-notifications-count"),
]