from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from users.models import CustomUser
from .models import Notification
from .serializers import NotificationSerializer


class NotificationCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        title = request.data.get("title")
        body = request.data.get("body")
        notification_type = request.data.get("type")
        user_id = request.data.get("user")

        if not all([title, body, notification_type, user_id]):
            return Response(
                {"error": "title, body, type, and user are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification = Notification.objects.create(
            title=title,
            body=body,
            type=notification_type,
            user=user,
        )

        data = NotificationSerializer(notification).data
        group_name = f"notifications_{user.id}"

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "notification": data,
            }
        )

        return Response(data, status=status.HTTP_201_CREATED)


class MyNotificationsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by("-created_at")


class MyNotificationDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkAllNotificationsAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        updated_count = Notification.objects.filter(
            user=request.user,
            isRead=False
        ).update(isRead=True)

        return Response(
            {
                "message": "All notifications marked as read",
                "updated_count": updated_count,
                "unread_count": 0,
            },
            status=status.HTTP_200_OK,
        )


class UnreadNotificationsCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(
            user=request.user,
            isRead=False
        ).count()

        return Response(
            {
                "user_id": request.user.id,
                "unread_count": unread_count,
            },
            status=status.HTTP_200_OK,
        )


def send_notification(title, body, notification_type, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)

        notification = Notification.objects.create(
            title=title,
            body=body,
            type=notification_type,
            user=user,
        )

        data = NotificationSerializer(notification).data
        group_name = f"notifications_{user_id}"
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "notification": data,
            }
        )

        return data

    except CustomUser.DoesNotExist:
        return {"error": "User not found"}
    except Exception as e:
        return {"error": f"Error creating notification: {e}"}