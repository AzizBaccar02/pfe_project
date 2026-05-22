from django.db import models


class NotificationType(models.TextChoices):
    PROPOSAL_STATUS   = "PROPOSAL_STATUS",   "Proposal Status"
    NEW_MESSAGE       = "NEW_MESSAGE",       "New Message"
    MATCH_CREATED     = "MATCH_CREATED",     "Match Created"
    AGENT_LIKED_OFFER = "AGENT_LIKED_OFFER", "Agent Liked Offer"
    CLIENT_REJECTED   = "CLIENT_REJECTED",   "Client Rejected"


class Notification(models.Model):
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    isRead     = models.BooleanField(default=False)
    type       = models.CharField(max_length=30, choices=NotificationType.choices)
    data       = models.JSONField(default=dict, blank=True)
    user       = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    class Meta:
        ordering = ["-created_at"]