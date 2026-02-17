from django.db import models


class ChatStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "ACTIVE"
    CLOSED = "CLOSED", "CLOSED"


class Chat(models.Model):
    createdAt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=ChatStatus.choices)
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
        on_delete=models.CASCADE,
        related_name="chats"
    )


class Message(models.Model):
    content = models.TextField()
    sentAt = models.DateTimeField(auto_now_add=True)
    isRead = models.BooleanField(default=False)
    chat = models.ForeignKey(
        "chats.Chat",
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
