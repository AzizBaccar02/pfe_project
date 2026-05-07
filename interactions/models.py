from django.conf import settings
from django.db import models


class OfferReactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"


class OffreReaction(models.Model):
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offer_reactions",
    )
    offre = models.ForeignKey(
        "offers.Offre",
        on_delete=models.CASCADE,
        related_name="reactions",
    )

    react = models.BooleanField()
    message = models.TextField(blank=True)
    proposedPrice = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=OfferReactionStatus.choices,
        default=OfferReactionStatus.PENDING,
    )

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "offre"],
                name="unique_agent_offer_reaction",
            )
        ]

    def __str__(self):
        return f"{self.agent.email} -> {self.offre.title} ({self.status})"