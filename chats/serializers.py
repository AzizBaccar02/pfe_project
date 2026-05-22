# chats/serializers.py

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
            "clientArchived",
            "agentArchived",
            "clientMuted",
            "agentMuted",
            "clientCustomTitle",
            "agentCustomTitle",
            "blockedBy",
            "blockedAt",
        ]
        read_only_fields = [
            "id",
            "createdAt",
            "blockedBy",
            "blockedAt",
        ]


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