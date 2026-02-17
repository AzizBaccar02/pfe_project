from django.db import models


class NotificationType(models.TextChoices):
    PROPOSAL_STATUS = "PROPOSAL_STATUS", "PROPOSAL_STATUS"
    NEW_MESSAGE = "NEW_MESSAGE", "NEW_MESSAGE"
    MATCH_CREATED = "MATCH_CREATED", "MATCH_CREATED"


class Notification(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    isRead = models.BooleanField(default=False)
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
