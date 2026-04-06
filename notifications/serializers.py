from rest_framework import serializers
from users.models import CustomUser
from .models import Notification



class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "body",
            "created_at",
            "isRead",
            "type",
            "user",
        ]
        read_only_fields = ["id", "created_at", "isRead", "user"]