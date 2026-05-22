from django.urls import path
from .views import (
    NotificationCreateAPIView,
    MyNotificationsAPIView,
    MyNotificationDetailAPIView,
    MarkNotificationAsReadAPIView,
    MarkAllNotificationsAsReadAPIView,
    UnreadNotificationsCountAPIView,
)

urlpatterns = [
    path("notifications/",                 NotificationCreateAPIView.as_view(),        name="create-notification"),
    path("notifications/me/",              MyNotificationsAPIView.as_view(),            name="my-notifications"),
    # static paths BEFORE <int:id>
    path("notifications/me/read-all/",     MarkAllNotificationsAsReadAPIView.as_view(), name="mark-all-read"),
    path("notifications/me/unread-count/", UnreadNotificationsCountAPIView.as_view(),   name="unread-count"),
    path("notifications/me/<int:id>/",     MyNotificationDetailAPIView.as_view(),       name="notification-detail"),
    path("notifications/me/<int:id>/read/",MarkNotificationAsReadAPIView.as_view(),     name="mark-one-read"),
]