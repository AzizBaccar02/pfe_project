# chats/models.py

from django.db import models


class ChatStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "ACTIVE"
    CLOSED = "CLOSED", "CLOSED"


class Chat(models.Model):
    createdAt = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=10,
        choices=ChatStatus.choices,
        default=ChatStatus.ACTIVE,
    )

    client = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="client_chats",
    )

    agent = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="agent_chats",
    )

    offreReaction = models.ForeignKey(
        "interactions.OffreReaction",
        on_delete=models.SET_NULL,
        related_name="chats",
        null=True,
        blank=True,
    )

    clientArchived = models.BooleanField(default=False)
    agentArchived = models.BooleanField(default=False)

    clientMuted = models.BooleanField(default=False)
    agentMuted = models.BooleanField(default=False)

    clientCustomTitle = models.CharField(max_length=120, blank=True, default="")
    agentCustomTitle = models.CharField(max_length=120, blank=True, default="")

    blockedBy = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        related_name="blocked_chats",
        null=True,
        blank=True,
    )
    blockedAt = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Chat {self.id} - client {self.client_id} / agent {self.agent_id}"


class Message(models.Model):
    content = models.TextField()
    sentAt = models.DateTimeField(auto_now_add=True)
    isRead = models.BooleanField(default=False)

    chat = models.ForeignKey(
        "chats.Chat",
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    def __str__(self):
        return f"Message {self.id} in chat {self.chat_id}"