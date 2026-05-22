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


def send_notification(title, body, notification_type, user_id, data=None):
    """
    Call this from any other Django app to create + push a notification.

    Example:
        from notifications.views import send_notification

        send_notification(
            title="Molka liked your offer",
            body='Molka is interested in "Test 11".',
            notification_type="AGENT_LIKED_OFFER",
            user_id=client.id,
            data={
                "action":         "agent_liked_offer",
                "offer_id":       offer.id,
                "offer_title":    offer.title,
                "agent_id":       agent.id,
                "agent_name":     agent.get_full_name(),
                "agent_email":    agent.email,
                "interaction_id": interaction.id,
            },
        )
    """
    try:
        user = CustomUser.objects.get(id=user_id)

        notification = Notification.objects.create(
            title=title,
            body=body,
            type=notification_type,
            user=user,
            data=data or {},
        )

        payload       = NotificationSerializer(notification).data
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"notifications_{user_id}",
            {"type": "send_notification", "notification": payload},
        )

        return payload

    except CustomUser.DoesNotExist:
        return {"error": "User not found"}
    except Exception as exc:
        return {"error": str(exc)}


class NotificationCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        title             = request.data.get("title")
        body              = request.data.get("body")
        notification_type = request.data.get("type")
        user_id           = request.data.get("user")

        if not all([title, body, notification_type, user_id]):
            return Response(
                {"error": "title, body, type, and user are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extra_data = request.data.get("data", {})
        result = send_notification(
            title=title,
            body=body,
            notification_type=notification_type,
            user_id=user_id,
            data=extra_data if isinstance(extra_data, dict) else {},
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)


class MyNotificationsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MyNotificationDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = NotificationSerializer
    lookup_field       = "id"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=id, user=request.user)
        except Notification.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        notification.isRead = True
        notification.save(update_fields=["isRead"])
        return Response(NotificationSerializer(notification).data)


class MarkAllNotificationsAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        updated = Notification.objects.filter(user=request.user, isRead=False).update(isRead=True)
        return Response({"message": "All notifications marked as read", "updated_count": updated, "unread_count": 0})


class UnreadNotificationsCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        count = Notification.objects.filter(user=request.user, isRead=False).count()
        return Response({"user_id": request.user.id, "unread_count": count})