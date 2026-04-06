from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from notifications.models import Notification


def create_and_send_notification(user, title, body, notification_type):
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        type=notification_type,
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_notifications_{user.id}",
        {
            "type": "send_notification",
            "notification": {
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "created_at": notification.created_at.isoformat(),
                "isRead": notification.isRead,
                "type": notification.type,
            },
        },
    )

    return notification