##chats/serializers.py

from rest_framework import serializers
from .models import Chat, Message


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = [
            "id",
            "createdAt",
            "status",
            "client",
            "agent",
            "offreReaction",
        ]
        read_only_fields = ["id", "createdAt"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "sentAt",
            "isRead",
            "chat",
            "sender",
        ]
        read_only_fields = ["id", "sentAt", "isRead", "sender", "chat"]